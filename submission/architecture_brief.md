# Support Ticket Triage Agent

## Architecture decisions

The console agent reads the full ordered conversation, calls read-only tools for customer history, knowledge retrieval and regional service status, then produces a typed JSON decision. One OpenAI GPT model handles extraction, urgency and the response draft; a bounded Responses API function-call loop preserves tool results. Schema and reference validation are separate from generation. Human approval is application-owned; proposed replies and handoffs are never executed by this prototype.

Four short, fictional KB documents use inspectable lexical retrieval. A vector database is unnecessary for this scope; hybrid/embedding retrieval can replace the search implementation later. Customer scope is bound to the input ticket. Urgency follows impact, affected scope and time pressure rather than plan, anger or error code alone. All unresolved issues are retained. Service status is a limited observation, not proof of customer access; no root cause, refund or repair is invented.

## Failure handling

Missing data or tool errors remain explicit unknowns. Invalid JSON, skipped required lookups and unavailable citations trigger bounded correction; refusal, incomplete output, API failure or exhausted limits return human-review status without a decision. Transient requests have bounded retries and timeouts. Input and tool results are treated as untrusted data. Source-ID validation does not prove sentence-level groundedness, so human review remains necessary. Production logging would require redaction, access control and retention rules.

## Production evaluation

Use held-out, expert-labeled English/Thai tickets, including multi-message escalation, mixed issues, conflicting or stale docs, calm outages, angry minor requests, failed tools and prompt injection. Measure critical-ticket recall, urgency confusion, routing and extraction accuracy, retrieval relevance, unsupported claims, latency, cost and human overrides. Grade tool traces to locate failure sources. Start in shadow mode before enabling any outbound execution.

## Validation and limitations

37 offline integration/failure tests and all three scripted sample checks passed. Demo decisions are prepared fixtures; they do not measure model intelligence. The real GPT adapter is implemented; a live attempt returned credit_balance_exhausted, so no successful model decision has been verified. Tools use mock data; automated remediation and approval execution are outside scope.
