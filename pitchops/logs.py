"""Structured JSON logging (Cloud Logging picks up `severity`)."""

from __future__ import annotations

import json
import sys
from datetime import UTC, datetime
from typing import Any


def log(event: str, severity: str = "INFO", **fields: Any) -> None:
    rec = {"ts": datetime.now(UTC).isoformat(), "severity": severity, "event": event, **fields}
    print(json.dumps(rec, default=str), file=sys.stderr, flush=True)
