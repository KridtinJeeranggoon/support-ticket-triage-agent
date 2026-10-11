# Verification record

Validated locally on 11 October 2026 (Asia/Bangkok) with Python 3.12.14 and Pydantic 2.13.5.

| Check | Result | Limit |
|---|---|---|
| Offline unittest suite | 45 tests passed | Scripted model and HTTP responses |
| Console demo | All 3 assignment tickets completed | Prepared decision fixtures, not GPT reasoning |
| Sample evaluation rubric | 3 of 3 demo tickets passed | Tiny sample and prototype issue labels |
| Mock integrations | Customer history, KB lookup and status lookup executed | No real external service |
| Approval boundary | All sample outputs pending human approval; replies not sent | No approval/execution integration |
| Windows launcher | Enterprise demo passed under PowerShell 7 default and Legacy native argument passing; missing-key errors remain readable with exit code 2 | Full Windows PowerShell 5.1 script execution could not be tested because its local execution policy prohibits scripts |
| Thai console output | Thai text remains correct when starting with OEM code page 437; original encoding is restored | Tested with PowerShell 7 |
| Configuration | Candidate verified key lookup from .env; loader tests cover precedence, quotes/BOM, placeholders and redacted errors | Configuration check sends no API request and does not establish key validity or credits |
| Submission brief | One A4 page rendered and visually inspected | Written against the implemented prototype |
| HTTP 429 handling | Quota/rate classification, bounded Retry-After and batch stopping tested | Simulated provider error bodies |
| First successful live GPT attempt | ticket-001 completed using GPT-4.1 mini and actual calls to two mock tools | Review found wrong reply language, unverified-charge wording and an overly broad access label; revisions await a fresh full sample run |

Passing offline tests establishes the tested program behavior, not production accuracy or calibrated confidence. The first live completion establishes an API/tool round trip; its semantic defects show why completion is not a quality verdict. Prompt-injection robustness and sentence-level groundedness have not been established across a representative dataset. No GitHub repository, customer message, refund or service change was created by this project.
