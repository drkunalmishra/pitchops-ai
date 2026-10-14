"""Structured JSON logging (Cloud Logging picks up `severity`)."""

from __future__ import annotations

import json
import sys
from datetime import UTC, datetime
from typing import Any


def log(event: str, **fields: Any) -> None:
    """log("x", severity="WARNING", k=v, ...) — severity defaults to INFO."""
    severity = fields.pop("severity", "INFO")
    rec = {"ts": datetime.now(UTC).isoformat(), "severity": severity, "event": event, **fields}
    print(json.dumps(rec, default=str), file=sys.stderr, flush=True)
