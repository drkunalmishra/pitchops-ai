"""Minimal YouTube Data API v3 client. Every call goes through QuotaLedger. No media downloads, ever."""

from __future__ import annotations

from typing import Any

import httpx
from tenacity import retry, retry_if_exception, stop_after_attempt, wait_exponential

from pitchops.youtube.quota import QuotaExhausted, QuotaLedger

BASE = "https://www.googleapis.com/youtube/v3"


def _retryable(e: BaseException) -> bool:
    return isinstance(e, httpx.HTTPStatusError) and e.response.status_code >= 500


class YouTubeClient:
    def __init__(self, api_key: str, ledger: QuotaLedger, timeout: float = 20.0) -> None:
        self.ledger = ledger
        # Key goes in a header, never in the URL, so it can never leak via logged URLs or exceptions.
        self._http = httpx.Client(timeout=timeout, headers={"X-Goog-Api-Key": api_key})

    def call(self, method: str, **params: Any) -> dict[str, Any]:
        """method like 'channels.list' -> GET /channels."""
        if not self.ledger.can_spend(method):
            raise QuotaExhausted("QUOTA_EXHAUSTED")
        self.ledger.spend(method)  # charged even if the call fails, like YouTube does
        return self._get(method.split(".")[0], params)

    @retry(retry=retry_if_exception(_retryable), stop=stop_after_attempt(3),
           wait=wait_exponential(multiplier=1, max=10), reraise=True)
    def _get(self, resource: str, params: dict[str, Any]) -> dict[str, Any]:
        r = self._http.get(f"{BASE}/{resource}", params=params)
        r.raise_for_status()
        return dict(r.json())

    def close(self) -> None:
        self.ledger.flush()
        self._http.close()
