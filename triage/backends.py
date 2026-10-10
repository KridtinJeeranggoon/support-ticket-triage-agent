"""Interchangeable Responses API and deterministic fixture transports."""

import json
import math
import os
import random
import time
import urllib.error
import urllib.request
from datetime import datetime, timezone
from email.utils import parsedate_to_datetime
from pathlib import Path
from typing import Protocol

from .tools import PROJECT_ROOT


class BackendError(RuntimeError):
    def __init__(self, message: str, stop_batch: bool = False):
        super().__init__(message)
        self.stop_batch = stop_batch


QUOTA_CODES = {
    "insufficient_quota", "billing_hard_limit_reached", "quota_exceeded",
    "credit_balance_exhausted", "organization_spend_limit_exceeded",
    "project_spend_limit_exceeded", "organization_usage_limit_exceeded",
}
RATE_CODES = {"rate_limit_exceeded", "slow_down"}


def classify_api_error(exc: urllib.error.HTTPError) -> tuple[str, str]:
    """Read a small error body, but expose only allowlisted diagnostic labels."""

    try:
        body = json.loads(exc.read(8192).decode("utf-8"))
        error = body.get("error", {}) if isinstance(body, dict) else {}
        if not isinstance(error, dict):
            return "unknown", "unclassified"
        code, kind = error.get("code"), error.get("type")
        if isinstance(code, str) and code in QUOTA_CODES:
            return "quota", code
        if kind == "insufficient_quota":
            return "quota", "insufficient_quota"
        if isinstance(code, str) and code in RATE_CODES:
            return "rate", code
        if kind == "rate_limit_error":
            return "rate", "rate_limit_error"
    except (OSError, ValueError, AttributeError, TypeError):
        pass
    return "unknown", "unclassified"


def retry_after_seconds(headers) -> float | None:
    """Accept Retry-After seconds or an HTTP date; ignore malformed values."""

    value = headers.get("Retry-After") if headers is not None else None
    if not isinstance(value, str):
        return None
    try:
        delay = float(value)
        return max(0, delay) if math.isfinite(delay) else None
    except ValueError:
        try:
            deadline = parsedate_to_datetime(value)
            if deadline.tzinfo is None:
                deadline = deadline.replace(tzinfo=timezone.utc)
            return max(0, (deadline - datetime.now(timezone.utc)).total_seconds())
        except (ValueError, TypeError, OverflowError):
            return None


class Backend(Protocol):
    mode: str
    model: str

    def respond(self, payload: dict) -> dict: ...


class OpenAIBackend:
    """Small standard-library REST adapter; no hidden SDK conversation state."""

    mode = "openai"
    endpoint = "https://api.openai.com/v1/responses"

    def __init__(self, model: str | None = None, timeout: float = 30, retries: int = 2,
                 max_retry_delay: float = 30):
        self.model = model or os.getenv("OPENAI_MODEL", "gpt-4.1-mini")
        self._key = os.getenv("OPENAI_API_KEY")
        if not self._key:
            raise BackendError("OPENAI_API_KEY is not set. Use --mode demo for an offline walkthrough.")
        self.timeout = timeout
        self.retries = retries
        self.max_retry_delay = max_retry_delay

    def respond(self, payload: dict) -> dict:
        body = json.dumps({**payload, "model": self.model}, ensure_ascii=False).encode("utf-8")
        for attempt in range(self.retries + 1):
            request = urllib.request.Request(
                self.endpoint, data=body, method="POST",
                headers={"Authorization": f"Bearer {self._key}", "Content-Type": "application/json"},
            )
            try:
                with urllib.request.urlopen(request, timeout=self.timeout) as response:
                    value = json.loads(response.read().decode("utf-8"))
                if not isinstance(value, dict):
                    raise BackendError("OpenAI returned an invalid response object.")
                return value
            except urllib.error.HTTPError as exc:
                category, code = classify_api_error(exc)
                server_delay = retry_after_seconds(exc.headers)
                status = exc.code
                exc.close()
                if status == 429 and category == "quota":
                    raise BackendError(
                        f"OpenAI HTTP 429 ({code}). API quota/billing is unavailable. "
                        "Check API credits and organization/project limits; retrying will not fix this.",
                        stop_batch=True,
                    ) from None
                transient = (status == 429 and category == "rate") or status in {500, 502, 503, 504}
                if transient and attempt < self.retries:
                    base_delay = max(2 ** attempt, server_delay or 0)
                    if base_delay <= self.max_retry_delay:
                        delay = min(self.max_retry_delay, base_delay + random.uniform(0, 0.25))
                        time.sleep(delay)
                        continue
                    raise BackendError(
                        f"OpenAI HTTP {status} ({code}). Retry delay exceeds the configured "
                        f"{self.max_retry_delay:g}s cap; defer this run rather than retry too early.",
                        stop_batch=True,
                    ) from None
                if status == 429:
                    detail = ("Temporary rate limit; retry later and reduce request/token rate."
                              if category == "rate" else
                              "The cause is unclassified; check API credits and limits before retrying.")
                    raise BackendError(f"OpenAI HTTP 429 ({code}). {detail}", stop_batch=True) from None
                # Do not print API response bodies, authorization headers or ticket text.
                raise BackendError(f"OpenAI HTTP {status}; no decision was executed.",
                                   stop_batch=status in {401, 403}) from None
            except (urllib.error.URLError, TimeoutError, OSError) as exc:
                if attempt < self.retries:
                    time.sleep(2 ** attempt)
                    continue
                raise BackendError("OpenAI connection failed or timed out; human review is required.") from None
            except (ValueError, UnicodeError):
                raise BackendError("OpenAI returned malformed JSON; human review is required.") from None
        raise BackendError("OpenAI retry limit reached.")


class DemoBackend:
    """Scripts model outputs for the exact assignment fixtures, not an AI model.

    Real tool execution, validation and approval policy still use the production
    orchestration code. This mode proves plumbing, not GPT reasoning quality.
    """

    mode = "demo"
    model = "scripted_fixture_no_llm"

    def __init__(self, ticket: dict, data_dir: Path | None = None):
        data_dir = data_dir or PROJECT_ROOT / "data"
        original = json.loads((data_dir / "tickets.json").read_text(encoding="utf-8"))
        if ticket not in original:
            raise BackendError("Demo only supports unchanged assignment tickets. Use OpenAI mode for custom tickets.")
        fixtures = json.loads((data_dir / "demo_responses.json").read_text(encoding="utf-8"))
        self.fixture = fixtures[ticket["ticket_id"]]
        self.calls = 0

    def respond(self, payload: dict) -> dict:
        self.calls += 1
        if self.calls == 1:
            output = [
                {"type": "function_call", "id": f"fc_demo_{i}", "call_id": f"call_demo_{i}",
                 "name": call["name"], "arguments": json.dumps(call["arguments"], ensure_ascii=False)}
                for i, call in enumerate(self.fixture["tool_calls"], start=1)
            ]
        else:
            output = [{"type": "message", "role": "assistant", "content": [
                {"type": "output_text", "text": json.dumps(self.fixture["decision"], ensure_ascii=False)}
            ]}]
        return {"status": "completed", "output": output}
