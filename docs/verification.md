# Verification record

Validated locally on 11 October 2026 (Asia/Bangkok) with Python 3.12.14 and Pydantic 2.13.5.

| Check | Result | Limit |
|---|---|---|
| Offline unittest suite | 54 tests passed | Scripted model and HTTP responses; no paid requests |
| Console demo | All 3 assignment tickets completed | Prepared decision fixtures, not GPT reasoning |
| Sample evaluation rubric | 3 of 3 demo tickets and 3 of 3 latest live tickets passed | Tiny sample; narrow phrase checks do not establish groundedness |
| Mock integrations | Customer history, KB lookup and status lookup executed | No real external service |
| Approval boundary | All sample outputs pending human approval; replies not sent | No approval/execution integration |
| Windows launcher | Enterprise demo passed under PowerShell 7 default and Legacy native argument passing; missing-key errors remain readable with exit code 2 | Full Windows PowerShell 5.1 script execution could not be tested because its local execution policy prohibits scripts |
| Thai console output | Thai text remains correct when starting with OEM code page 437; original encoding is restored | Tested with PowerShell 7 |
| Configuration | Candidate verified key lookup from .env; loader tests cover precedence, quotes/BOM, placeholders and redacted errors | Configuration check sends no API request and does not establish key validity or credits |
| Submission brief | One A4 page rendered and visually inspected | Written against the implemented prototype |
| HTTP 429 handling | Quota/rate classification, bounded Retry-After and batch stopping tested | Simulated provider error bodies |
| Source-bound evidence | Latest live outputs use exact message quotes and available references; regression tests cover invalid pairs and invented transaction observations | Other generated sentences can still misinterpret sources |
| Latest live GPT run | All three tickets completed: high/specialist, critical/human, medium/specialist; 2/3/2 successful mock calls | Manual review found unsupported capture and action/commitment wording; see live_review.md |

Passing offline tests establishes the tested program behavior, not production accuracy or calibrated confidence. The live run establishes API/tool round trips and sample rubric compliance; its semantic defects show why completion is not a quality verdict. Prompt-injection robustness and sentence-level groundedness have not been established across a representative dataset. No GitHub repository, customer message, refund or service change was created by this project.
