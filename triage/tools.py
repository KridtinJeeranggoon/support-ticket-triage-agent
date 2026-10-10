"""Read-only mock integrations. Retrieval deliberately uses lexical matching."""

import json
import re
from pathlib import Path

from pydantic import Field, ValidationError

from .models import Contract, strict_schema


PROJECT_ROOT = Path(__file__).resolve().parent.parent


class HistoryArgs(Contract):
    customer_id: str = Field(min_length=1, max_length=100)


class SearchArgs(Contract):
    query: str = Field(min_length=1, max_length=1000)
    limit: int = Field(ge=1, le=5)


class StatusArgs(Contract):
    region: str = Field(min_length=1, max_length=100)


TOOL_CONTRACTS = {
    "get_customer_history": (HistoryArgs, "Read the current customer's plan and support history. Pass only the customer_id on the ticket."),
    "search_knowledge_base": (SearchArgs, "Search fictional FAQ/runbooks using issue-focused terms. Returns relevant text and document IDs; scores are lexical match counts, not probabilities."),
    "check_service_status": (StatusArgs, "Read a mock public status snapshot for a region. A green result does not verify a customer's access."),
}


def tool_definitions() -> list[dict]:
    return [
        {"type": "function", "name": name, "description": description,
         "strict": True, "parameters": strict_schema(contract)}
        for name, (contract, description) in TOOL_CONTRACTS.items()
    ]


class ToolRegistry:
    def __init__(self, customer_id: str, data_dir: Path | None = None):
        self.customer_id = customer_id
        self.data_dir = data_dir or PROJECT_ROOT / "data"

    def _read(self, filename: str):
        return json.loads((self.data_dir / filename).read_text(encoding="utf-8"))

    def call(self, name: str, raw_arguments: str) -> dict:
        if name not in TOOL_CONTRACTS:
            return {"ok": False, "error": "unknown_tool"}
        if not isinstance(raw_arguments, str) or len(raw_arguments) > 4000:
            return {"ok": False, "error": "invalid_arguments"}
        contract = TOOL_CONTRACTS[name][0]
        try:
            args = contract.model_validate_json(raw_arguments)
        except (ValidationError, ValueError):
            return {"ok": False, "error": "invalid_arguments"}

        try:
            if name == "get_customer_history":
                if args.customer_id != self.customer_id:
                    return {"ok": False, "error": "customer_scope_violation"}
                record = self._read("customers.json").get(args.customer_id)
                if record is None:
                    return {"ok": False, "error": "customer_not_found"}
                return {"ok": True, "source_type": "mock_customer_history",
                        "customer_id": args.customer_id, "customer": record}

            if name == "search_knowledge_base":
                query = args.query.casefold()
                english_words = set(re.findall(r"[a-z0-9]+", query))
                matches = []
                for doc in self._read("knowledge_base.json"):
                    # Latin words match whole tokens; Thai terms match substrings.
                    score = sum(
                        (word.casefold() in english_words)
                        if re.fullmatch(r"[a-z0-9]+", word.casefold())
                        else (word.casefold() in query)
                        for word in doc["keywords"]
                    )
                    if score:
                        matches.append({"id": doc["id"], "title": doc["title"],
                                        "content": doc["content"], "match_score": score,
                                        "source_type": doc["source_type"]})
                matches.sort(key=lambda item: (-item["match_score"], item["id"]))
                return {"ok": True, "query": args.query,
                        "score_type": "keyword_match_count_not_confidence",
                        "matches": matches[:args.limit]}

            snapshot = self._read("service_status.json").get(args.region)
            if snapshot is None:
                return {"ok": False, "error": "region_not_found"}
            return {"ok": True, "source_type": "mock_status_snapshot",
                    "region": args.region, "status": snapshot}
        except (OSError, ValueError, KeyError, TypeError):
            return {"ok": False, "error": "source_unavailable"}
