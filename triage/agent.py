"""Bounded model -> tool -> model loop with application-owned validation."""

import json
import time
from pathlib import Path

from pydantic import ValidationError

from .backends import Backend, BackendError
from .evidence import available_references, decision_schema
from .language import reply_language
from .models import ApprovedPolicy, Decision, Ticket
from .reply import reply_violation
from .tools import PROJECT_ROOT, ToolRegistry, tool_definitions


class DecisionError(ValueError):
    pass


def validate_references(decision: Decision, ticket: Ticket, trace: list[dict]) -> None:
    """Enforce real reference membership, not merely well-formed JSON."""

    if decision.ticket_id != ticket.ticket_id:
        raise DecisionError("Decision ticket_id does not match input.")
    expected_language = reply_language("\n".join(message.text for message in ticket.messages))
    if expected_language and reply_language(decision.draft_reply) != expected_language:
        language_name = "English" if expected_language == "en" else "Thai"
        raise DecisionError(f"For this ticket, draft_reply must be written in {language_name}.")
    violation = reply_violation(decision.draft_reply)
    if violation:
        raise DecisionError(violation)

    allowed = available_references(ticket, trace)
    kb_ids = set(allowed["knowledge_base"])
    if ticket.customer_id not in allowed["customer_history"]:
        raise DecisionError("A successful customer history lookup is required.")
    if not any(entry["name"] == "search_knowledge_base" and entry["result"].get("ok") for entry in trace):
        raise DecisionError("A successful knowledge base search is required.")
    if not set(decision.knowledge_base_ids).issubset(kb_ids):
        raise DecisionError("Decision cites a document that was not retrieved.")

    for item in decision.evidence:
        if item.reference not in allowed[item.source]:
            choices = json.dumps(allowed[item.source], ensure_ascii=False)
            raise DecisionError(f"Evidence source '{item.source}' must use one of these exact references: {choices}.")
        if item.source == "customer_report":
            index = int(item.reference.split(":")[1]) - 1
            if item.observation != ticket.messages[index].text:
                raise DecisionError("Customer-report observations must quote the referenced message exactly, without inferring captured payments or other facts.")
    malfunctions = {"appearance_malfunction", "access_failure", "upgrade_entitlement_failure", "possible_service_incident"}
    if decision.urgency == "low" and malfunctions.intersection(decision.issue_types):
        raise DecisionError("An unresolved malfunction requires at least medium urgency under this prototype policy; low is for informational questions or feature requests only.")
    if decision.urgency == "critical" and decision.recommended_action != "escalate_to_human":
        raise DecisionError("Critical tickets require an urgent human escalation proposal.")
    if decision.recommended_action == "auto_respond" and (not kb_ids or not decision.knowledge_base_ids):
        raise DecisionError("An automatic answer proposal requires retrieved supporting documentation.")
    if decision.recommended_action == "auto_respond" and (
        decision.urgency != "low" or decision.suspected_causes or decision.unknowns
    ):
        raise DecisionError("Automatic answer proposals are limited to low-impact, supported answers without unresolved diagnostic questions.")


class TriageAgent:
    def __init__(self, backend: Backend, max_rounds: int = 8, max_tool_calls: int = 12,
                 data_dir: Path | None = None):
        self.backend = backend
        self.max_rounds = max_rounds
        self.max_tool_calls = max_tool_calls
        self.data_dir = data_dir
        self.instructions = (PROJECT_ROOT / "prompts" / "system.txt").read_text(encoding="utf-8")

    def run(self, ticket: Ticket) -> dict:
        started = time.monotonic()
        registry = ToolRegistry(ticket.customer_id, self.data_dir)
        trace, corrections = [], []
        conversation = [{"role": "user", "content": json.dumps(ticket.model_dump(), ensure_ascii=False)}]
        envelope = {"ticket_id": ticket.ticket_id, "mode": self.backend.mode,
                    "model": self.backend.model, "approval": ApprovedPolicy().model_dump()}
        language = reply_language("\n".join(message.text for message in ticket.messages))
        instructions = self.instructions
        if language:
            name = "English" if language == "en" else "Thai"
            instructions += f"\nTICKET-SPECIFIC LANGUAGE: draft_reply must be written in {name}."

        try:
            for _ in range(self.max_rounds):
                references = json.dumps(available_references(ticket, trace), ensure_ascii=False)
                response = self.backend.respond({
                    "instructions": instructions + "\nAVAILABLE EVIDENCE REFERENCES: " + references,
                    "input": conversation,
                    "tools": tool_definitions(),
                    "tool_choice": "auto",
                    "parallel_tool_calls": False,
                    "store": False,
                    "max_output_tokens": 4000,
                    "text": {"format": {"type": "json_schema", "name": "triage_decision",
                                        "strict": True, "schema": decision_schema(ticket, trace)}},
                })
                if response.get("status") != "completed":
                    raise BackendError("Model response was incomplete or failed.")
                output = response.get("output")
                if not isinstance(output, list) or any(not isinstance(item, dict) for item in output):
                    raise BackendError("Model output has an invalid shape.")
                # Keep every output item, including reasoning items, for stateless continuation.
                conversation.extend(output)
                calls = [item for item in output if item.get("type") == "function_call"]
                if calls:
                    if len(trace) + len(calls) > self.max_tool_calls:
                        raise BackendError("Tool call limit reached.")
                    for call in calls:
                        if not all(isinstance(call.get(key), str) for key in ("name", "arguments", "call_id")):
                            raise BackendError("Model supplied a malformed tool call.")
                        result = registry.call(call["name"], call["arguments"])
                        trace.append({"name": call["name"], "arguments": call["arguments"], "result": result})
                        conversation.append({"type": "function_call_output", "call_id": call["call_id"],
                                             "output": json.dumps(result, ensure_ascii=False)})
                    continue

                text_parts = []
                for item in output:
                    if item.get("type") != "message":
                        continue
                    contents = item.get("content", [])
                    if not isinstance(contents, list) or any(not isinstance(content, dict) for content in contents):
                        raise BackendError("Model message content has an invalid shape.")
                    for content in contents:
                        if content.get("type") == "refusal":
                            raise BackendError("The model refused the ticket; human review is required.")
                        if content.get("type") == "output_text":
                            if not isinstance(content.get("text"), str):
                                raise BackendError("Model output text has an invalid shape.")
                            text_parts.append(content["text"])
                try:
                    decision = Decision.model_validate_json("".join(text_parts))
                    validate_references(decision, ticket, trace)
                except (ValidationError, DecisionError, ValueError) as exc:
                    detail = str(exc) if isinstance(exc, DecisionError) else "Decision JSON does not match the contract."
                    corrections.append(detail)
                    conversation.append({"role": "user", "content": "Application validation failed: " + detail +
                                         " Correct the decision using the available evidence references. "
                                         "Do not repeat successful tool calls merely to fix citation formatting."})
                    continue

                return {**envelope, "run_status": "completed", "decision": decision.model_dump(),
                        "tool_trace": trace, "validation_notes": corrections,
                        "latency_seconds": round(time.monotonic() - started, 3)}
            raise BackendError("Model round limit reached without a valid decision.")
        except (BackendError, OSError, ValueError, TypeError, KeyError) as exc:
            reason = str(exc) if isinstance(exc, BackendError) else "Unexpected processing failure; human review is required."
            return {**envelope, "run_status": "needs_human_review", "decision": None,
                    "tool_trace": trace, "validation_notes": corrections, "failure_reason": reason,
                    "stop_batch": isinstance(exc, BackendError) and exc.stop_batch,
                    "latency_seconds": round(time.monotonic() - started, 3)}
