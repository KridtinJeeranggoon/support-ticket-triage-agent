"""Interchangeable Responses API and deterministic fixture transports."""

import json
import os
import time
import urllib.error
import urllib.request
from pathlib import Path
from typing import Protocol

from .tools import PROJECT_ROOT


class BackendError(RuntimeError):
    pass


class Backend(Protocol):
    mode: str
    model: str

    def respond(self, payload: dict) -> dict: ...


class OpenAIBackend:
    """Small standard-library REST adapter; no hidden SDK conversation state."""

    mode = "openai"
    endpoint = "https://api.openai.com/v1/responses"

    def __init__(self, model: str | None = None, timeout: float = 30, retries: int = 2):
        self.model = model or os.getenv("OPENAI_MODEL", "gpt-4.1-mini")
        self._key = os.getenv("OPENAI_API_KEY")
        if not self._key:
            raise BackendError("OPENAI_API_KEY is not set. Use --mode demo for an offline walkthrough.")
        self.timeout = timeout
        self.retries = retries

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
                if exc.code in {429, 500, 502, 503, 504} and attempt < self.retries:
                    time.sleep(2 ** attempt)
                    continue
                # Do not print API response bodies, authorization headers or ticket text.
                raise BackendError(f"OpenAI HTTP {exc.code}; no decision was executed.") from None
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
