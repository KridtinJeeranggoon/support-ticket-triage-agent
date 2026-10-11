# Support Ticket Triage Agent

## Architecture decisions

The Python console agent reads the full ordered conversation, calls read-only customer-history, knowledge and regional-status tools, then produces a Pydantic-validated decision. One OpenAI GPT model handles extraction, urgency and drafting in a bounded Responses API tool loop. The output schema binds evidence references to available sources and customer evidence to exact message quotes. Human approval is application-owned; proposed replies and handoffs are never executed.

Four short, fictional KB documents use inspectable lexical retrieval. A vector database is unnecessary for this scope; hybrid/embedding retrieval can replace the search implementation later. Customer scope is bound to the input ticket. Urgency follows impact, affected scope and time pressure rather than plan, anger or error code alone. Policy retains unresolved issues and prohibits invented root causes, refunds or repairs. Service status is a limited observation, not proof of customer access.

## Failure handling

Missing data or tool errors remain explicit unknowns. Invalid JSON, skipped lookups and unavailable citations trigger bounded correction; refusal, incomplete output, API failure or exhausted limits return human-review status without a decision. Transient requests have bounded retries and timeouts. Input and tool results are untrusted data. Narrow English/Thai script and action-phrase checks catch known regressions; source validation does not prove sentence-level groundedness. Production logging requires redaction, access control and retention rules.

## Production evaluation

Use held-out, expert-labeled English/Thai tickets, including multi-message escalation, mixed issues, conflicting or stale docs, calm outages, angry minor requests, failed tools and prompt injection. Measure critical-ticket recall, urgency confusion, routing and extraction accuracy, retrieval relevance, unsupported claims, latency, cost and human overrides. Grade tool traces to locate failure sources. Start in shadow mode before enabling any outbound execution.

## Validation and limitations

54 offline tests and all three scripted checks passed. A live GPT-4.1 mini run completed all three cases with 2/3/2 mock tool calls and passed the small automated rubric. Manual review still found an unsupported captured-payment claim and implied investigation/commitment wording. Raw outputs and proposed reviewer edits are recorded separately. This demonstrates the need for human review, not production accuracy. Automated remediation and approval execution are outside scope.
