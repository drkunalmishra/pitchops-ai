"""Vertex AI Gemini client (google-genai, vertexai=True). Never uses AI Studio / Developer API keys.

generate_json(): budget check -> call (retries on 429/5xx) -> JSON-schema validation -> one repair retry.
Every call is logged to llm_calls with an ESTIMATED cost from usage_metadata x the price table in config.
"""

from __future__ import annotations

import json
import time
from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Any

import jsonschema
from google import genai
from google.genai import errors, types
from tenacity import retry, retry_if_exception, stop_after_attempt, wait_exponential

from pitchops.config import Settings, get_settings
from pitchops.gemini.budget import BigQuerySpendStore, GeminiBudget
from pitchops.logs import log

MEDIA_RES = {
    "low": types.MediaResolution.MEDIA_RESOLUTION_LOW,
    "medium": types.MediaResolution.MEDIA_RESOLUTION_MEDIUM,
    "high": types.MediaResolution.MEDIA_RESOLUTION_HIGH,
}


class SchemaValidationFailed(Exception):
    pass


def estimate_cost(settings: Settings, model_id: str, tokens_in: int, tokens_out: int) -> float:
    pin, pout = settings.price_for(model_id)
    return round(tokens_in / 1e6 * pin + tokens_out / 1e6 * pout, 8)


def _retryable(e: BaseException) -> bool:
    return isinstance(e, errors.APIError) and (e.code == 429 or (e.code or 0) >= 500)


def youtube_part(url: str, start_s: int | None = None, end_s: int | None = None) -> types.Part:
    """A public YouTube URL as file_data (no download). Optional offsets via video_metadata."""
    meta = None
    if start_s is not None or end_s is not None:
        meta = types.VideoMetadata(start_offset=f"{start_s or 0}s",
                                   end_offset=f"{end_s}s" if end_s is not None else None)
    return types.Part(file_data=types.FileData(file_uri=url, mime_type="video/*"), video_metadata=meta)


@dataclass
class CallResult:
    data: Any
    tokens_in: int
    tokens_out: int
    cost_usd_est: float
    latency_ms: int
    model_id: str
    attempts: int = 1
    raw_text: str = field(default="", repr=False)


class GeminiClient:
    def __init__(self, job: str, run_id: str, settings: Settings | None = None,
                 budget: GeminiBudget | None = None, log_to_bq: bool = True,
                 phase_prefix: str | None = None, phase_cap: float | None = None) -> None:
        self.s = settings or get_settings()
        self.job, self.run_id, self.log_to_bq = job, run_id, log_to_bq
        self.budget = budget or GeminiBudget(BigQuerySpendStore(), self.s.gemini_budget_usd,
                                             self.s.gemini_daily_usd, phase_prefix=phase_prefix,
                                             phase_cap=phase_cap, ttl_s=20.0)
        self.client = genai.Client(vertexai=True, project=self.s.gcp_project_id, location=self.s.gemini_location)
        self.embed_client = genai.Client(vertexai=True, project=self.s.gcp_project_id, location=self.s.gcp_region)

    # ---- low level -------------------------------------------------------------------------
    @retry(retry=retry_if_exception(_retryable), stop=stop_after_attempt(4),
           wait=wait_exponential(multiplier=2, max=30), reraise=True)
    def _generate(self, model: str, contents: Any, config: types.GenerateContentConfig) -> Any:
        return self.client.models.generate_content(model=model, contents=contents, config=config)

    def _log(self, model: str, prompt_version: str, tin: int, tout: int, cost: float, ms: int,
             status: str) -> None:
        self.budget.record(cost)
        log("llm_call", job=self.job, model_id=model, tokens_in=tin, tokens_out=tout,
            cost_usd_est=cost, latency_ms=ms, status=status)
        if self.log_to_bq:
            from pitchops.bq import insert_rows

            now = datetime.now(UTC).isoformat()
            insert_rows("llm_calls", [{"ts": now, "job": self.job, "model_id": model,
                                       "prompt_version": prompt_version, "tokens_in": tin, "tokens_out": tout,
                                       "cost_usd_est": cost, "latency_ms": ms, "status": status,
                                       "run_id": self.run_id, "ingested_at": now}])

    def generate(self, model: str, contents: Any, config: types.GenerateContentConfig,
                 prompt_version: str = "adhoc") -> tuple[Any, int, int, float, int]:
        """One budgeted, logged call. Returns (response, tokens_in, tokens_out, cost, latency_ms)."""
        self.budget.check()
        t0 = time.monotonic()
        try:
            resp = self._generate(model, contents, config)
        except Exception:
            self._log(model, prompt_version, 0, 0, 0.0, int((time.monotonic() - t0) * 1000), "ERROR")
            raise
        ms = int((time.monotonic() - t0) * 1000)
        um = resp.usage_metadata
        tin = int(getattr(um, "prompt_token_count", 0) or 0)
        tout = int(getattr(um, "candidates_token_count", 0) or 0) + int(getattr(um, "thoughts_token_count", 0) or 0)
        cost = estimate_cost(self.s, model, tin, tout)
        self._log(model, prompt_version, tin, tout, cost, ms, "OK")
        return resp, tin, tout, cost, ms

    # ---- JSON with schema validation + one repair --------------------------------------------
    def generate_json(self, model: str, contents: Any, schema: dict[str, Any], media_resolution: str = "low",
                      prompt_version: str = "adhoc", temperature: float = 0.2, system: str | None = None,
                      thinking: str | None = None, validator: Any = None) -> CallResult:
        """thinking: None (model default) or a Gemini 3 thinking level such as "minimal" / "low".
        validator: optional callable(data) -> list[str] of extra semantic errors (empty = valid)."""
        cfg = types.GenerateContentConfig(
            response_mime_type="application/json", response_json_schema=schema,
            media_resolution=MEDIA_RES[media_resolution], temperature=temperature, system_instruction=system,
            thinking_config=types.ThinkingConfig(thinking_level=types.ThinkingLevel(thinking.upper())) if thinking else None)
        contents = contents if isinstance(contents, list) else [contents]
        tot_in = tot_out = tot_ms = 0
        tot_cost = 0.0
        last_err = ""
        for attempt in (1, 2):
            call_contents = contents
            if attempt == 2:
                call_contents = contents + [
                    f"Your previous reply was not valid JSON for the required schema ({last_err[:500]}). "
                    "Reply again with ONLY valid JSON that matches the schema."]
            resp, tin, tout, cost, ms = self.generate(model, call_contents, cfg, prompt_version)
            tot_in, tot_out, tot_cost, tot_ms = tot_in + tin, tot_out + tout, tot_cost + cost, tot_ms + ms
            text = resp.text or ""
            try:
                data = json.loads(text)
                jsonschema.validate(data, schema)
                extra = validator(data) if validator else []
                if extra:
                    raise jsonschema.ValidationError("; ".join(extra)[:800])
                return CallResult(data, tot_in, tot_out, round(tot_cost, 8), tot_ms, model, attempt, text)
            except (json.JSONDecodeError, jsonschema.ValidationError) as e:
                last_err = f"{type(e).__name__}: {getattr(e, 'message', str(e))}"
                log("llm_schema_invalid", severity="WARNING", model_id=model, attempt=attempt, error=last_err)
        raise SchemaValidationFailed(last_err)

    # ---- embeddings ----------------------------------------------------------------------------
    def embed(self, texts: list[str], model: str | None = None, prompt_version: str = "embed") -> list[list[float]]:
        model = model or self.s.embedding_model_id
        self.budget.check()
        t0 = time.monotonic()
        resp = self.embed_client.models.embed_content(model=model, contents=texts)
        ms = int((time.monotonic() - t0) * 1000)
        vecs = [list(e.values or []) for e in (resp.embeddings or [])]
        tin = sum(int(getattr(getattr(e, "statistics", None), "token_count", 0) or 0)
                  for e in (resp.embeddings or [])) or sum(len(t) // 4 for t in texts)
        cost = estimate_cost(self.s, model, tin, 0)
        self._log(model, prompt_version, tin, 0, cost, ms, "OK")
        return vecs
