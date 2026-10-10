"""Bounded model -> tool -> model loop with application-owned validation."""

import json
import time
from pathlib import Path

from pydantic import ValidationError

from .backends import Backend, BackendError
from .models import ApprovedPolicy, Decision, Ticket, strict_schema
from .tools import PROJECT_ROOT, ToolRegistry, tool_definitions


class DecisionError(ValueError):
    pass


def validate_references(decision: Decision, ticket: Ticket, trace: list[dict]) -> None:
    """Enforce real reference membership, not merely well-formed JSON."""

    if decision.ticket_id != ticket.ticket_id:
        raise DecisionError("Decision ticket_id does not match input.")

    history_ids, kb_ids, status_regions = set(), set(), set()
    for entry in trace:
        result = entry["result"]
        if not result.get("ok"):
            continue
        if entry["name"] == "get_customer_history":
            history_ids.add(result["customer_id"])
        elif entry["name"] == "search_knowledge_base":
            kb_ids.update(item["id"] for item in result["matches"])
        elif entry["name"] == "check_service_status":
            status_regions.add(result["region"])

    if ticket.customer_id not in history_ids:
        raise DecisionError("A successful customer history lookup is required.")
    if not any(entry["name"] == "search_knowledge_base" and entry["result"].get("ok") for entry in trace):
        raise DecisionError("A successful knowledge base search is required.")
    if not set(decision.knowledge_base_ids).issubset(kb_ids):
        raise DecisionError("Decision cites a document that was not retrieved.")

    allowed = {
        "customer_report": {f"message:{index}" for index in range(1, len(ticket.messages) + 1)},
        "customer_history": history_ids,
        "knowledge_base": kb_ids,
        "service_status": status_regions,
    }
    for item in decision.evidence:
        if item.reference not in allowed[item.source]:
            raise DecisionError("Evidence references a source that was not available.")
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

        try:
            for _ in range(self.max_rounds):
                response = self.backend.respond({
                    "instructions": self.instructions,
                    "input": conversation,
                    "tools": tool_definitions(),
                    "tool_choice": "auto",
                    "parallel_tool_calls": False,
                    "store": False,
                    "max_output_tokens": 4000,
                    "text": {"format": {"type": "json_schema", "name": "triage_decision",
                                        "strict": True, "schema": strict_schema(Decision)}},
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
                                         " Use the permitted tools and produce a corrected decision."})
                    continue

                return {**envelope, "run_status": "completed", "decision": decision.model_dump(),
                        "tool_trace": trace, "validation_notes": corrections,
                        "latency_seconds": round(time.monotonic() - started, 3)}
            raise BackendError("Model round limit reached without a valid decision.")
        except (BackendError, OSError, ValueError, TypeError, KeyError) as exc:
            reason = str(exc) if isinstance(exc, BackendError) else "Unexpected processing failure; human review is required."
            return {**envelope, "run_status": "needs_human_review", "decision": None,
                    "tool_trace": trace, "validation_notes": corrections, "failure_reason": reason,
                    "latency_seconds": round(time.monotonic() - started, 3)}
