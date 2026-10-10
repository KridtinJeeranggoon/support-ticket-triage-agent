# Support Ticket Triage Agent

A Python console agent that reads the complete ticket conversation, looks up customer context and relevant knowledge, and proposes a grounded support response or handoff. Every outbound action awaits human approval. It never sends a reply, changes billing, repairs a system, or closes a ticket.

## Quick start

Requires Python 3.11+ and Pydantic 2. On Windows, `py` can replace `python` if Python is not on PATH.

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
.\.venv\Scripts\python.exe -m triage --mode demo --trace --output runs/demo.json
```

On macOS/Linux:

```sh
python3 -m venv .venv
.venv/bin/python -m pip install -r requirements.txt
.venv/bin/python -m triage --mode demo --trace --output runs/demo.json
```

`run.ps1` is an optional Windows convenience launcher. It prefers a project virtual environment, then a compatible installed interpreter, then the Codex bundled interpreter when present. It does not install packages or change execution policy. From this folder, run `& .\run.ps1 -Mode demo`.

## Real GPT mode

The default mode is `openai`; missing credentials produce an error rather than silently switching to demo. No API key is included in this repository. `.env.example` documents environment variables; this application does **not** load `.env` automatically.

PowerShell, without putting the key into the command history:

```powershell
$secureKey = Read-Host 'OpenAI API key' -AsSecureString
$env:OPENAI_API_KEY = [System.Net.NetworkCredential]::new('', $secureKey).Password
$env:OPENAI_MODEL = 'gpt-4.1-mini'
.\.venv\Scripts\python.exe -m triage --mode openai --trace --output runs/openai.json
Remove-Item Env:OPENAI_API_KEY
```

macOS/Linux:

```sh
read -r -s OPENAI_API_KEY
export OPENAI_API_KEY
export OPENAI_MODEL=gpt-4.1-mini
.venv/bin/python -m triage --mode openai --trace --output runs/openai.json
unset OPENAI_API_KEY
```

The default GPT model supports function calling and structured output. Change `OPENAI_MODEL` to another compatible OpenAI GPT model if needed. The small REST adapter uses Python's standard library and the Responses endpoint directly; there is no additional SDK dependency. Each run has bounded model/tool calls, request timeouts, and at most two retries for transient API failures. Real GPT mode makes chargeable requests.

**Verification status:** offline integration and failure-handling tests pass. A live OpenAI call has not been performed because no API key was available. The API adapter has been tested with simulated HTTP responses, which does not establish service compatibility or model quality.

## Modes and sample data

| Mode | Model output | Tools | What it demonstrates |
|---|---|---|---|
| `openai` | Real OpenAI GPT | Read-only local mock integrations | Actual model/tool workflow, once credentials are supplied |
| `demo` | Scripted responses for the three unchanged assignment tickets | The same actual local tool code | Orchestration, validation and approval policy; not LLM accuracy |

`data/tickets.json` preserves all four messages in each supplied case. IDs were assigned locally. Customer attributes come from the assignment and are available through the history tool. Knowledge documents and service-status snapshots are explicitly fictional fixtures, not verified product policies or live telemetry. There is no access to Ooca infrastructure or payment systems.

Demo rejects modified/custom tickets instead of returning a fixture answer for unrelated input. For a custom ticket in OpenAI mode, provide a JSON array using the `Ticket` contract and add the corresponding customer fixture to `data/customers.json`:

```powershell
.\.venv\Scripts\python.exe -m triage --mode openai --tickets data/custom_tickets.json --trace
.\.venv\Scripts\python.exe -m triage --mode demo --ticket-id ticket-002 --trace
```

Relative time labels such as "just now" are preserved; no absolute dates were invented.

## Architecture

```text
Ordered ticket messages
        |
        v
GPT with system prompt and tool schemas
        | function_call
        v
Validated, allowlisted read-only tool execution
        | function_call_output
        +------------------> GPT (repeat within limits)
                                |
                                v
                     Structured decision JSON
                                |
                                v
               Local schema and reference validation
                                |
                                v
             Application-owned human approval state
```

The three tools are:

| Tool | Input | Output | Decision support |
|---|---|---|---|
| `get_customer_history` | Current ticket's `customer_id` | Plan, tenure and known history | Customer context without assuming plan alone determines urgency |
| `search_knowledge_base` | Issue-focused `query`, `limit` 1-5 | Relevant document text, IDs and keyword-match counts | Grounded guidance and cited source membership |
| `check_service_status` | `region` | Public status and limits of the mock snapshot | Preserve conflicts between reported failures and a green status page |

All definitions include JSON Schema and executable implementations in `triage/tools.py`. Successful history lookup and KB search are required by code before a final decision. Status lookup for regional access issues is instructed in the prompt; reference validation prevents citing a status result that was not actually obtained. Tool errors are returned as errors and never interpreted as healthy status. Customer scope is fixed by the input ticket, not chosen by the model.

Retrieval uses deterministic keyword matching over four short documents, including Thai terms. OpenAI mode combines retrieved text with generation, but this prototype has **no vector database or embedding model** and does not claim semantic search. A match count is not confidence. A larger multilingual knowledge base would justify evaluating hybrid/embedding retrieval behind the same tool contract.

## Decision policy

- `critical`: severe/broad core access loss requiring immediate incident review.
- `high`: urgent individual impact, repeated/disputed payments, missing paid access or a near-term deadline.
- `medium`: unresolved limited-impact malfunction without an immediate deadline.
- `low`: informational questions or feature requests without an unresolved malfunction.

These are prototype policy choices, not a supplied company SLA. The highest-impact unresolved issue determines ticket urgency; all issue types are retained. Plan, sentiment and an error code alone are insufficient. The demo labels are high/billing specialist, critical/incident owner and medium/product support respectively.

`Decision` separates evidence, suspected causes, unknowns, next steps and the customer reply draft. `auto_respond`, `route_to_specialist` and `escalate_to_human` are recommendations. Critical decisions must propose escalation; automatic answer proposals are restricted to low-impact supported answers without unresolved diagnostic questions. The user-selected approval policy means even an `auto_respond` recommendation is queued for approval. There is no approval/execution integration in this prototype.

Application validation checks schemas, matching ticket/customer IDs and that cited sources were actually available. It does **not** prove that every generated sentence faithfully interprets its source. The prompt and human review address that residual risk; production evaluation must explicitly measure it. Root-cause diagnosis and automated remediation are outside this assignment's implemented scope.

If a model refuses, outputs invalid JSON, skips required tools, cites unavailable sources, or exhausts limits, the run either requests a bounded correction or returns `needs_human_review` with no valid decision. Nothing is executed.

## Tests and evaluation

```powershell
.\.venv\Scripts\python.exe -m unittest discover -s tests -v
.\.venv\Scripts\python.exe -m triage.evaluate example_results/demo.json
# After a real model run:
.\.venv\Scripts\python.exe -m triage.evaluate runs/openai.json
```

The offline tests cover the full function-call loop, customer isolation, Thai lookup, missing data, invented citations, required tool use, schema failures, refusal/incomplete output, loop limits, human approval and REST error handling. The three-case rubric permits high or critical for the billing case but requires human/specialist involvement; the access case must be critical; the appearance case must retain the malfunction and feature request. Exact issue labels are a prototype taxonomy and may need semantic review when evaluating real model outputs.

Issue types use a fixed prototype taxonomy in the output schema, with `other` for unsupported categories. A valid taxonomy value can still be semantically wrong; classification accuracy requires reference labels and human review.

The three assignment cases are a smoke test, not a sufficient benchmark. Before production, evaluate held-out expert-labeled cases including calm outages, angry low-impact requests, multi-issue conversations, stale/conflicting KB, failed tools, missing metadata, Thai/English variation and prompt injection. Measure critical-ticket recall, urgency confusion, routing correctness, extraction accuracy, unsupported claims, retrieval relevance, latency, token cost and human overrides. Review traces to distinguish tool/data failures from model errors. Start in shadow mode and keep a rollback path.

Local result files contain support content and tool observations. Use synthetic data here. Production requires access control, redaction and retention rules before recording real customer conversations.

## Files to read

1. `triage/models.py`: input/output contracts and approval state.
2. `triage/tools.py`: tool schemas and mock implementations.
3. `prompts/system.txt`: behavioral policy.
4. `triage/agent.py`: model/tool loop and validation.
5. `triage/backends.py`: real API adapter and offline demo.
6. `triage/__main__.py`: console entry point.
7. `tests/test_triage.py`: evidence of failure handling.

The separate Thai learning guide is for walkthroughs; it is not the one-page submission brief. `submission/architecture_brief.pdf` is the one-page write-up. `example_results/demo.json` is explicitly labeled demo output. `docs/verification.md` records the actual validation performed.

## Submission

Publish this source folder as a GitHub repository after review, or send the provided source ZIP with its `.git` directory if GitHub is unavailable. Do not include an API key, `.env`, virtual environment or real customer logs. Git history is initialized locally; no GitHub repository has been created. Interview availability and the email receipt date must be provided by the candidate.

## Official API references

- [Function calling](https://developers.openai.com/api/docs/guides/function-calling)
- [Structured outputs](https://developers.openai.com/api/docs/guides/structured-outputs?api-mode=responses)
- [GPT-4.1 mini](https://developers.openai.com/api/docs/models/gpt-4.1-mini)
- [Evaluation best practices](https://developers.openai.com/api/docs/guides/evaluation-best-practices)
