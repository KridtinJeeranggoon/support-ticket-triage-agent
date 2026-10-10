"""Terminal entry point. No outbound reply, handoff or repair is executed."""

import argparse
import json
import sys
from pathlib import Path

from pydantic import ValidationError

from .agent import TriageAgent
from .backends import BackendError, DemoBackend, OpenAIBackend
from .models import Ticket
from .tools import PROJECT_ROOT


def main() -> int:
    parser = argparse.ArgumentParser(description="Support ticket triage; all actions await human approval.")
    parser.add_argument("--mode", choices=["openai", "demo"], default="openai")
    parser.add_argument("--tickets", type=Path, default=PROJECT_ROOT / "data" / "tickets.json")
    parser.add_argument("--ticket-id", help="Process only the selected ticket ID.")
    parser.add_argument("--output", type=Path, help="Optional JSON result file.")
    parser.add_argument("--trace", action="store_true", help="Show tools, retrieved IDs and validation notes.")
    args = parser.parse_args()
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")

    try:
        raw_tickets = json.loads(args.tickets.read_text(encoding="utf-8"))
        if not isinstance(raw_tickets, list) or not raw_tickets:
            raise ValueError("Ticket file must be a nonempty JSON array.")
        tickets = [Ticket.model_validate(item) for item in raw_tickets]
        if len({ticket.ticket_id for ticket in tickets}) != len(tickets):
            raise ValueError("Ticket IDs must be unique.")
        if args.ticket_id:
            tickets = [ticket for ticket in tickets if ticket.ticket_id == args.ticket_id]
            if not tickets:
                raise ValueError("The selected ticket ID was not found.")
        # Validate the file and configuration before any chargeable requests.
        shared_backend = OpenAIBackend() if args.mode == "openai" else None
        results = []
        for index, ticket in enumerate(tickets):
            backend = shared_backend or DemoBackend(ticket.model_dump())
            result = TriageAgent(backend).run(ticket)
            results.append(result)
            print(f"\n{ticket.ticket_id} | {result['mode']} | {result['run_status']}")
            if result["decision"]:
                decision = result["decision"]
                print(f"Urgency: {decision['urgency']} | Action: {decision['recommended_action']}")
                print(f"Issues: {', '.join(decision['issue_types'])} | Sentiment: {decision['sentiment']}")
                print(f"Summary: {decision['summary']}")
                print(f"Why: {decision['urgency_reason']}")
                print(f"Draft reply (not sent): {decision['draft_reply']}")
            else:
                print(result["failure_reason"])
            print("Execution: pending_human_approval; customer_reply_sent=false")
            if args.trace:
                for entry in result["tool_trace"]:
                    print(f"  TOOL {entry['name']} | ok={entry['result'].get('ok')}")
                    for match in entry["result"].get("matches", []):
                        print(f"    {match['id']} | keyword_match_count={match['match_score']}")
                for note in result["validation_notes"]:
                    print(f"  VALIDATION {note}")
            if result.get("stop_batch"):
                remaining = len(tickets) - index - 1
                print(f"\nStopped batch: resolve the API issue before retrying. {remaining} remaining ticket(s) were not processed.")
                break
        if args.output:
            args.output.parent.mkdir(parents=True, exist_ok=True)
            args.output.write_text(json.dumps(results, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
            print(f"\nSaved {len(results)} result(s) to {args.output}")
        return 0 if all(result["run_status"] == "completed" for result in results) else 2
    except ValidationError:
        print("Input validation failed. Check ticket fields, message text and size limits.", file=sys.stderr)
        return 2
    except (OSError, ValueError, BackendError) as exc:
        print(f"Cannot run: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
