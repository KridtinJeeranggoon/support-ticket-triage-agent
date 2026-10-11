"""A narrow guard for known false action claims in a read-only prototype.

This is not a semantic truth checker. Unmatched wording and other factual claims
still require human review before any outbound reply.
"""

import re


ACTION_CLAIMS = re.compile(
    r"\b(?:we|i)(?:\s+have|['’]ve)\s+(?:already\s+)?(?:escalated|routed|forwarded|sent|refunded|fixed|resolved)\b"
    r"|\b(?:we|i)\s+(?:are|am)\s+(?:escalating|routing|forwarding|refunding|fixing)\b"
    r"|\b(?:case|ticket)\s+has\s+been\s+(?:escalated|routed|forwarded|sent)\b"
    r"|(?:เรา|ทางเรา)ได้(?:ส่ง|ดำเนินการ|คืนเงิน|แก้ไข)"
    r"|(?:เรา|ทางเรา)(?:กำลังส่งเรื่อง|กำลังส่งต่อ|กำลังคืนเงิน)",
    re.IGNORECASE,
)
UPDATE_PROMISES = re.compile(
    r"\b(?:respond|reply|update|response|resolved|resolution)\b[^.!?\n]{0,60}\b(?:soon|shortly)\b",
    re.IGNORECASE,
)


def reply_violation(reply: str) -> str | None:
    if ACTION_CLAIMS.search(reply):
        return ("Draft claims a handoff or other action is occurring/completed, but this prototype has no execution tools. "
                "Describe only a proposed next step, such as 'The next step is an urgent specialist review'.")
    if UPDATE_PROMISES.search(reply):
        return "Draft promises an update or resolution soon/shortly without an established SLA. Remove the time promise."
    return None
