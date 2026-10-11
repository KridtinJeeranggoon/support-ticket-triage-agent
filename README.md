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

`run.ps1` is an optional Windows convenience launcher. It prefers a project virtual environment, then a compatible installed interpreter, then the Codex bundled interpreter when present. Its runtime probe is a Python file, avoiding embedded-quote differences in native argument passing, and unavailable interpreters are skipped. It does not install packages or change execution policy. From this folder, run `& .\run.ps1 -Mode demo`.

## Real GPT mode

The default mode is `openai`; missing credentials produce an error rather than silently switching to demo. No API key is included in this repository. The CLI automatically loads `.env` from the project root in OpenAI mode. Copy `.env.example` to `.env` and replace the key placeholder locally. Nonempty process environment variables take precedence over file values, so an existing terminal key is not silently replaced.

The small configuration loader supports `NAME=value`, quoted values, comments and an optional `export` prefix for `OPENAI_API_KEY` and `OPENAI_MODEL` only. It does not execute shell code, interpolate variables, or change the parent terminal environment. The private `.env` file remains ignored by Git and excluded from the source ZIP.

Check configuration without a chargeable API call or printing credentials:

```powershell
& .\run.ps1 -Mode openai -CheckConfig
# Or with the project interpreter:
.\.venv\Scripts\python.exe -m triage --mode openai --check-config
```

This checks that a key is configured, not whether the provider accepts it or the account has credits. `--env-file path/to/config.env` selects another configuration file if needed.

Alternatively, set process variables in PowerShell without putting the key into command history:

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

**Verification status:** 54 offline integration and failure-handling tests pass. The latest live GPT-4.1 mini run completed all three tickets and passed the small automated rubric using actual model-selected calls to mock tools. Manual review still found an unsupported "captured" payment claim and implied investigation/commitment wording. This is evidence of residual semantic defects, not production readiness. See `docs/live_review.md` for the original findings and separately proposed reviewer edits; `example_results/openai.json` preserves the raw output.

The Windows launcher temporarily aligns PowerShell native-output decoding with Python's UTF-8 output, then restores the original console encoding. A regression test starts with OEM code page 437 and verifies the actual Thai text inside PowerShell, not just the subprocess exit code. Result JSON files are written as UTF-8 independently of terminal display.

## Troubleshooting HTTP 429

Run one ticket first: `& .\run.ps1 -Mode openai -TicketId ticket-001`.

| Diagnostic label | Meaning | Recovery |
|---|---|---|
| `insufficient_quota`, credit/spend/usage limit labels | API quota or billing availability | Check the API organization's credits and applicable project/organization limits; repeated requests do not resolve this |
| `rate_limit_exceeded`, `slow_down`, `rate_limit_error` | Temporary traffic throttling | Pace requests; follow Retry-After when supplied |
| `unclassified` | Insufficient recognized diagnostic information | Check API limits and account state; do not assume the cause |

Quota failures are not retried. Temporary throttling uses bounded backoff with jitter, respecting Retry-After. A required delay above the 30-second retry-delay cap defers the run rather than retrying early. Account/access failures and exhausted or unclassified 429 responses stop the batch; remaining tickets are not processed. Only allowlisted error labels are displayed; raw messages, credentials and customer text are excluded. A `needs_human_review` result caused by API failure is an operational fallback, not an AI classification of customer urgency. See [OpenAI error codes](https://developers.openai.com/api/docs/guides/error-codes).

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

- `critical`: broad core access loss or another severe ongoing impact requiring immediate accountable human review.
- `high`: urgent individual impact, repeated/disputed payments, missing paid access or a near-term deadline.
- `medium`: unresolved limited-impact malfunction without an immediate deadline.
- `low`: informational questions or feature requests without an unresolved malfunction.

These are prototype policy choices, not a supplied company SLA. The highest-impact unresolved issue determines ticket urgency; all issue types are retained. Plan, sentiment and an error code alone are insufficient. The demo labels are high/billing specialist, critical/incident owner and medium/product support respectively.

`Decision` separates evidence, suspected causes, unknowns, next steps and the customer reply draft. `auto_respond`, `route_to_specialist` and `escalate_to_human` are recommendations. Critical decisions must propose escalation; automatic answer proposals are restricted to low-impact supported answers without unresolved diagnostic questions. The user-selected approval policy means even an `auto_respond` recommendation is queued for approval. There is no approval/execution integration in this prototype.

`triage/evidence.py` builds the output schema for each model round from the ticket and successful tool results. Evidence source/reference pairs are constrained together: message evidence uses an exact quote of that message, while KB/history/status references can only use returned IDs. Application validation repeats these checks, including exact quotes when long inputs require quote enums to be omitted from the API schema. A successful KB search may return no matches; it establishes that a lookup occurred, not that an answer is supported.

Application validation checks matching ticket/customer IDs and rejects low urgency for unresolved malfunctions under this prototype policy. These checks do **not** prove that every summary, hypothesis or draft sentence faithfully interprets its source. Root-cause diagnosis and automated remediation are outside this assignment's implemented scope.

For the supplied English/Thai conversations, `triage/language.py` selects the predominant script, adds a ticket-specific reply instruction and rejects a reply with the wrong script. This is a narrow heuristic, not general language identification: it cannot distinguish English from other Latin-script languages and does not constrain ambiguous inputs. Prompt wording explicitly attributes unverified financial reports to the customer, separates missing Pro entitlement from core access failure, and avoids claims of executed handoffs or promised update times. These semantic requirements still need human review.

`triage/reply.py` rejects specific known phrases such as "We are escalating", "We have sent" and "เราได้ส่งเรื่อง" and unsupported "response soon/shortly" wording. This is a narrow pattern guard, not a semantic truth checker: unmatched paraphrases, investigation claims, financial assertions and other commitments may still slip through. A correction uses the existing tool results within the same bounded loop. Human approval and production groundedness evaluation remain necessary.

If a model refuses, outputs invalid JSON, skips required tools, cites unavailable sources, or exhausts limits, the run either requests a bounded correction or returns `needs_human_review` with no valid decision. Nothing is executed.

## Tests and evaluation

```powershell
.\.venv\Scripts\python.exe -m unittest discover -s tests -v
.\.venv\Scripts\python.exe -m triage.evaluate example_results/demo.json
# After a real model run:
.\.venv\Scripts\python.exe -m triage.evaluate runs/openai.json
```

The offline tests cover the full function-call loop, customer isolation, Thai lookup, missing data, source/reference binding, exact customer quotes, reply-language/action regressions, required tool use, schema failures, refusal/incomplete output, loop limits, human approval and REST error handling. The three-case rubric permits high or critical for the billing case but requires human/specialist involvement; the access case must be critical; the appearance case must be medium and retain the malfunction and feature request. An additional `how_to` label is allowed for its appearance-option questions. The rubric also checks the narrow reply guard; it does not establish full semantic correctness.

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
8. `triage/evidence.py`, `triage/language.py`, `triage/reply.py`: source binding and narrow reply checks.

The separate Thai learning guide is for walkthroughs; it is not the one-page submission brief. `submission/architecture_brief.pdf` is the one-page write-up. `example_results/demo.json` is explicitly labeled demo output. `docs/verification.md` records the actual validation performed.

## Submission

Publish this source folder as a GitHub repository after review, or send the provided source ZIP with its `.git` directory if GitHub is unavailable. Do not include an API key, `.env`, virtual environment or real customer logs. Git history is initialized locally; no GitHub repository has been created. Interview availability and the email receipt date must be provided by the candidate.

## Official API references

- [Function calling](https://developers.openai.com/api/docs/guides/function-calling)
- [Structured outputs](https://developers.openai.com/api/docs/guides/structured-outputs?api-mode=responses)
- [GPT-4.1 mini](https://developers.openai.com/api/docs/models/gpt-4.1-mini)
- [Evaluation best practices](https://developers.openai.com/api/docs/guides/evaluation-best-practices)
#   s u p p o r t - t i c k e t - t r i a g e - a g e n t  
 #   s u p p o r t - t i c k e t - t r i a g e - a g e n t  
 