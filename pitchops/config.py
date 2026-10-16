"""Central settings, loaded from env / .env. Never log secret values."""

from __future__ import annotations

import json
import re
from functools import lru_cache
from typing import Any

from pydantic import Field, SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict

# Gemini price table, USD per 1M tokens (input, output). These are ESTIMATES used only by
# GeminiBudget to stop spend early; they are deliberately on the high side. Edit if pricing changes.
# Real spend is in Billing -> Reports.
DEFAULT_PRICES: dict[str, tuple[float, float]] = {
    "flash-lite": (0.10, 0.40),
    "flash": (0.50, 3.00),
    "pro": (2.50, 15.00),
    "embedding": (0.15, 0.0),
}


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    gcp_project_id: str = ""
    gcp_region: str = "us-central1"
    bq_dataset: str = "pitchops_corpus"
    firestore_database: str = "pitchops"
    gcs_bucket: str = ""  # defaults to {project}-pitchops

    youtube_api_key: SecretStr = SecretStr("")
    yt_daily_unit_cap: int = 9000

    # Gemini 3.x models are served only from the Vertex "global" endpoint (still Vertex AI, credit-covered).
    gemini_location: str = "global"
    gemini_model_flash: str = "gemini-3.8-flash"
    gemini_model_lite: str = "gemini-3.5-flash-lite"
    gemini_model_pro: str = "gemini-3.1-pro-preview"
    embedding_model_id: str = "gemini-embedding-001"
    gemini_budget_usd: float = 60.0
    gemini_daily_usd: float = 25.0
    gemini_phase_budget_usd_p3: float = 35.0  # raised from 30 by owner, 14 Oct
    total_project_cap_usd: float = 200.0
    # Optional JSON override: {"gemini-3.8-flash": [0.5, 3.0], ...}
    price_per_mtok_json: str = ""

    firebase_config_json: str = ""
    contact_email: str = ""
    cors_origins: str = Field(default="")
    # P7 media (D15/D16): verify prices in Cloud Billing; these are deliberately conservative estimates
    veo_model_id: str = "veo-3.1-fast-generate-001"
    veo_price_audio_per_sec: float = 0.15
    veo_price_silent_per_sec: float = 0.10
    imagen_model_id: str = "gemini-3.1-flash-image"  # Imagen is not offered to this project; Gemini image model
    imagen_price: float = 0.04  # per generated image (estimate)
    media_budget_usd: float = 120.0
    admin_emails: str = ""  # comma-separated; Firebase users with these emails (or custom claim admin) see Admin/QA

    @property
    def bucket(self) -> str:
        return self.gcs_bucket or f"{self.gcp_project_id}-pitchops"

    def table(self, name: str) -> str:
        return f"{self.gcp_project_id}.{self.bq_dataset}.{name}"

    def price_for(self, model_id: str) -> tuple[float, float]:
        """(in, out) USD per 1M tokens for a model id — explicit override first, then family."""
        if self.price_per_mtok_json:
            override = json.loads(self.price_per_mtok_json)
            if model_id in override:
                pin, pout = override[model_id]
                return float(pin), float(pout)
        mid = model_id.lower()
        if "embedding" in mid:
            return DEFAULT_PRICES["embedding"]
        if "lite" in mid:
            return DEFAULT_PRICES["flash-lite"]
        if "pro" in mid:
            return DEFAULT_PRICES["pro"]
        return DEFAULT_PRICES["flash"]

    def firebase_config(self) -> dict[str, Any]:
        return parse_js_object(self.firebase_config_json)


def parse_js_object(text: str) -> dict[str, Any]:
    """Parse a firebaseConfig snippet that may be a JS object literal (unquoted keys)."""
    text = text.strip().rstrip(";")
    if not text:
        return {}
    try:
        return dict(json.loads(text))
    except json.JSONDecodeError:
        quoted = re.sub(r'([{,]\s*)([A-Za-z_][A-Za-z0-9_]*)\s*:', r'\1"\2":', text)
        quoted = re.sub(r",\s*}", "}", quoted)
        return dict(json.loads(quoted))


@lru_cache
def get_settings() -> Settings:
    return Settings()
