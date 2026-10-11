"""A small, human-authored sample rubric, not a production-quality benchmark."""

import argparse
import json
from pathlib import Path

from .language import reply_language


RUBRIC = {
    "ticket-001": {"urgencies": {"high", "critical"},
                   "actions": {"route_to_specialist", "escalate_to_human"},
                   "issues": {"billing_dispute", "upgrade_entitlement_failure"},
                   "allowed_issues": {"billing_dispute", "upgrade_entitlement_failure"}, "language": "en"},
    "ticket-002": {"urgencies": {"critical"}, "actions": {"escalate_to_human"},
                   "issues": {"access_failure"},
                   "allowed_issues": {"access_failure", "possible_service_incident"}, "language": "th"},
    "ticket-003": {"urgencies": {"medium"}, "actions": {"route_to_specialist"},
                   "issues": {"appearance_malfunction", "feature_request"},
                   "allowed_issues": {"appearance_malfunction", "feature_request"}, "language": "en"},
}


def evaluate(results: list[dict]) -> dict:
    rows = []
    for ticket_id, expected in RUBRIC.items():
        matching = [item for item in results if item.get("ticket_id") == ticket_id]
        result = matching[0] if len(matching) == 1 else {}
        decision = result.get("decision") or {}
        successful_tools = {item["name"] for item in result.get("tool_trace", []) if item["result"].get("ok")}
        checks = {
            "completed": result.get("run_status") == "completed",
            "urgency": decision.get("urgency") in expected["urgencies"],
            "action": decision.get("recommended_action") in expected["actions"],
            "issues": expected["issues"].issubset(set(decision.get("issue_types", []))),
            "issue_taxonomy": set(decision.get("issue_types", [])).issubset(expected["allowed_issues"]),
            "reply_language": reply_language(decision.get("draft_reply", "")) == expected["language"],
            "required_tools": {"get_customer_history", "search_knowledge_base"}.issubset(successful_tools),
            "approval": result.get("approval", {}).get("execution_status") == "pending_human_approval"
                        and result.get("approval", {}).get("customer_reply_sent") is False,
        }
        if ticket_id == "ticket-002":
            checks["status_lookup"] = "check_service_status" in successful_tools
            checks["thai_reply"] = any("\u0e00" <= char <= "\u0e7f" for char in decision.get("draft_reply", ""))
        rows.append({"ticket_id": ticket_id, "checks": checks, "passed": all(checks.values())})
    return {"mode": "demo_fixture_checks" if results and all(item.get("mode") == "demo" for item in results)
                    else "model_sample_checks",
            "passed_tickets": sum(row["passed"] for row in rows), "total_tickets": len(rows),
            "results": rows,
            "limitation": "Three sample cases only. Exact issue labels are a prototype taxonomy; semantic review and groundedness checks still require a human. Demo checks do not measure LLM quality."}


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("results", type=Path)
    args = parser.parse_args()
    try:
        results = json.loads(args.results.read_text(encoding="utf-8"))
        if not isinstance(results, list):
            raise ValueError("Expected a result array.")
        report = evaluate(results)
    except (OSError, ValueError, TypeError, KeyError) as exc:
        parser.error(str(exc))
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 0 if report["passed_tickets"] == report["total_tickets"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
