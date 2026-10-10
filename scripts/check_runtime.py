"""Quiet interpreter probe, kept in a file to avoid shell quoting differences."""

import sys


if sys.version_info < (3, 11):
    sys.exit(1)

try:
    import pydantic

    parts = pydantic.__version__.split(".")
    compatible = int(parts[0]) == 2 and int(parts[1]) >= 7
except Exception:
    compatible = False

sys.exit(0 if compatible else 1)
