"""Versioned taxonomy (prompts/taxonomy_v2.json) loader."""

from __future__ import annotations

import json
from functools import lru_cache
from pathlib import Path
from typing import Any

PATH = Path(__file__).resolve().parents[2] / "prompts" / "taxonomy_v2.json"


@lru_cache
def taxonomy() -> dict[str, Any]:
    return dict(json.loads(PATH.read_text()))


def enum(name: str) -> list[str]:
    return list(taxonomy()[name])
