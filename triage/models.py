"""Contracts for input, tool-independent decisions, and executable policy."""

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


class Contract(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)


class Message(Contract):
    time_label: str = Field(min_length=1, max_length=100)
    text: str = Field(min_length=1, max_length=8000)


class Ticket(Contract):
    ticket_id: str = Field(min_length=1, max_length=100)
    customer_id: str = Field(min_length=1, max_length=100)
    messages: list[Message] = Field(min_length=1, max_length=30)


class Evidence(Contract):
    source: Literal["customer_report", "customer_history", "knowledge_base", "service_status"]
    reference: str = Field(min_length=1, max_length=200)
    observation: str = Field(min_length=1, max_length=2000)


class Decision(Contract):
    """What the model proposes. Approval is derived by application code."""

    ticket_id: str
    urgency: Literal["critical", "high", "medium", "low"]
    product: str = Field(min_length=1)
    issue_types: list[str] = Field(min_length=1)
    sentiment: Literal["positive", "neutral", "concerned", "frustrated", "angry", "mixed"]
    summary: str = Field(min_length=1)
    urgency_reason: str = Field(min_length=1)
    evidence: list[Evidence] = Field(min_length=1)
    suspected_causes: list[str]
    unknowns: list[str]
    recommended_action: Literal["auto_respond", "route_to_specialist", "escalate_to_human"]
    destination: str = Field(min_length=1)
    next_steps: list[str] = Field(min_length=1)
    draft_reply: str = Field(min_length=1)
    knowledge_base_ids: list[str]


class ApprovedPolicy(Contract):
    """Application-owned fields: a model cannot approve its own proposal."""

    approval_required: Literal[True] = True
    execution_status: Literal["pending_human_approval"] = "pending_human_approval"
    customer_reply_sent: Literal[False] = False


def strict_schema(model: type[BaseModel]) -> dict:
    """Normalize Pydantic's schema for the API's required-field strict mode."""

    schema = model.model_json_schema()

    def visit(node):
        if isinstance(node, dict):
            if node.get("type") == "object":
                node["additionalProperties"] = False
                node["required"] = list(node.get("properties", {}))
            for value in node.values():
                visit(value)
        elif isinstance(node, list):
            for value in node:
                visit(value)

    visit(schema)
    return schema
