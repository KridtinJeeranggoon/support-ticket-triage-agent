"""Load two local settings without executing config or exposing credentials."""

import os
import shlex
from dataclasses import dataclass, field
from pathlib import Path
from typing import Mapping


@dataclass(frozen=True)
class Settings:
    api_key: str | None = field(repr=False)
    model: str
    key_source: str


def load_settings(env_file: Path, environ: Mapping[str, str] | None = None) -> Settings:
    """Nonempty process variables take precedence over an explicit .env file.

    Supports KEY=value, quotes, comments and an optional 'export' prefix.
    Only OPENAI_API_KEY/OPENAI_MODEL are read. No interpolation or shell code.
    """

    environment = os.environ if environ is None else environ
    values = {}
    if env_file.exists():
        try:
            content = env_file.read_text(encoding="utf-8-sig")
        except (OSError, UnicodeError):
            raise ValueError("Cannot read the environment file as UTF-8.") from None
        for number, raw_line in enumerate(content.splitlines(), start=1):
            line = raw_line.strip()
            if not line or line.startswith("#"):
                continue
            if line.startswith("export "):
                line = line[7:].lstrip()
            name, separator, raw_value = line.partition("=")
            name = name.strip()
            if not separator:
                raise ValueError(f"Invalid environment file syntax on line {number}; expected NAME=value.")
            if name not in {"OPENAI_API_KEY", "OPENAI_MODEL"}:
                continue
            try:
                parts = shlex.split(raw_value, comments=True, posix=True)
                if len(parts) > 1:
                    raise ValueError()
            except ValueError:
                raise ValueError(f"Invalid environment file value on line {number}; check quotes and spacing.") from None
            if name in values:
                raise ValueError(f"Duplicate environment setting on line {number}.")
            values[name] = parts[0] if parts else ""

    environment_key = environment.get("OPENAI_API_KEY")
    key = environment_key or values.get("OPENAI_API_KEY") or None
    if key in {"replace_locally_do_not_commit", "YOUR_API_KEY", "your_api_key_here"}:
        raise ValueError("Replace the OPENAI_API_KEY placeholder locally before using OpenAI mode.")
    return Settings(
        api_key=key,
        model=environment.get("OPENAI_MODEL") or values.get("OPENAI_MODEL") or "gpt-4.1-mini",
        key_source="environment" if environment_key else (".env" if key else "missing"),
    )
