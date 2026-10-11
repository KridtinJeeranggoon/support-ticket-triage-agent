"""Build an evidence contract from input messages and successful tool results."""

from copy import deepcopy

from .models import Decision, Ticket, strict_schema


def available_references(ticket: Ticket, trace: list[dict]) -> dict[str, list[str]]:
    sources = {
        "customer_report": {f"message:{i}" for i in range(1, len(ticket.messages) + 1)},
        "customer_history": set(), "knowledge_base": set(), "service_status": set(),
    }
    for entry in trace:
        result = entry["result"]
        if not result.get("ok"):
            continue
        if entry["name"] == "get_customer_history":
            sources["customer_history"].add(result["customer_id"])
        elif entry["name"] == "search_knowledge_base":
            sources["knowledge_base"].update(item["id"] for item in result["matches"])
        elif entry["name"] == "check_service_status":
            sources["service_status"].add(result["region"])
    return {source: sorted(refs) for source, refs in sources.items()}


def decision_schema(ticket: Ticket, trace: list[dict]) -> dict:
    """Constrain source/reference pairs instead of asking the model to invent IDs.

    Customer evidence quotes the corresponding message exactly. For unusually
    long conversations, quote enums are omitted to stay below the API's schema
    enum-size limit; application validation still checks the exact quote.
    """

    schema = strict_schema(Decision)
    base = schema["$defs"]["Evidence"]
    choices = []
    quote_enums_fit = sum(len(message.text) for message in ticket.messages) <= 100000
    for index, message in enumerate(ticket.messages, start=1):
        choice = deepcopy(base)
        choice["properties"]["source"]["enum"] = ["customer_report"]
        choice["properties"]["reference"]["enum"] = [f"message:{index}"]
        if quote_enums_fit:
            choice["properties"]["observation"]["enum"] = [message.text]
        choices.append(choice)
    refs = available_references(ticket, trace)
    for source in ("customer_history", "knowledge_base", "service_status"):
        if not refs[source]:
            continue
        choice = deepcopy(base)
        choice["properties"]["source"]["enum"] = [source]
        choice["properties"]["reference"]["enum"] = refs[source]
        choices.append(choice)
    schema["$defs"]["Evidence"] = {"anyOf": choices}
    kb_field = schema["properties"]["knowledge_base_ids"]
    if refs["knowledge_base"]:
        kb_field["items"]["enum"] = refs["knowledge_base"]
    else:
        kb_field["maxItems"] = 0
    return schema
