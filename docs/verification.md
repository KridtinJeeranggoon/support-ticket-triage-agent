# Verification record

Validated locally on 11 October 2026 (Asia/Bangkok) with Python 3.12.14 and Pydantic 2.13.5.

| Check | Result | Limit |
|---|---|---|
| Offline unittest suite | 36 tests passed | Scripted model and HTTP responses |
| Console demo | All 3 assignment tickets completed | Prepared decision fixtures, not GPT reasoning |
| Sample evaluation rubric | 3 of 3 demo tickets passed | Tiny sample and prototype issue labels |
| Mock integrations | Customer history, KB lookup and status lookup executed | No real external service |
| Approval boundary | All sample outputs pending human approval; replies not sent | No approval/execution integration |
| Windows launcher | Enterprise demo passed under PowerShell 7 default and Legacy native argument passing; missing-key errors remain readable with exit code 2 | Full Windows PowerShell 5.1 script execution could not be tested because its local execution policy prohibits scripts |
| Submission brief | One A4 page rendered and visually inspected | Written against the implemented prototype |
| HTTP 429 handling | Quota/rate classification, bounded Retry-After and batch stopping tested | Simulated provider error bodies |
| Candidate's live GPT attempt | HTTP 429 reported on all 3 tickets; no valid decision | Original output did not include the error subtype |

Passing offline tests establishes the tested program behavior, not production accuracy, calibrated confidence or successful live API compatibility. No successful model decision has been verified. Prompt-injection robustness and sentence-level groundedness have not been established with a live model. No GitHub repository, customer message, refund or service change was created by this project.
