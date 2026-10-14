"""YouTube Data API v3 client. Every call goes through QuotaLedger. No media downloads, ever.

The key is sent as the X-Goog-Api-Key header (never in URLs). In Cloud Run it comes from Secret Manager
via --set-secrets; locally from .env.
"""

from __future__ import annotations

from collections.abc import Iterator
from typing import Any

import httpx
from tenacity import retry, retry_if_exception, stop_after_attempt, wait_exponential

from pitchops.youtube.quota import QuotaExhausted, QuotaLedger

BASE = "https://www.googleapis.com/youtube/v3"
QUOTA_REASONS = {"quotaExceeded", "dailyLimitExceeded", "rateLimitExceeded"}


def _retryable(e: BaseException) -> bool:
    if isinstance(e, httpx.TransportError):  # DNS / connect / read timeouts
        return True
    return isinstance(e, httpx.HTTPStatusError) and (e.response.status_code >= 500 or e.response.status_code == 429)


def _reason(r: httpx.Response) -> str:
    try:
        return str(r.json()["error"]["errors"][0]["reason"])
    except Exception:
        return ""


def chunks(xs: list[str], n: int = 50) -> Iterator[list[str]]:
    for i in range(0, len(xs), n):
        yield xs[i : i + n]


class YouTubeClient:
    def __init__(self, api_key: str, ledger: QuotaLedger, timeout: float = 20.0) -> None:
        self.ledger = ledger
        self._http = httpx.Client(timeout=timeout, headers={"X-Goog-Api-Key": api_key})

    def call(self, method: str, **params: Any) -> dict[str, Any]:
        """method like 'channels.list' -> GET /channels. Raises QuotaExhausted at the cap or on quotaExceeded."""
        if not self.ledger.can_spend(method):
            self.ledger.flush()
            raise QuotaExhausted("QUOTA_EXHAUSTED (ledger cap)")
        self.ledger.spend(method)  # charged even if the call fails, like YouTube does
        try:
            return self._get(method.split(".")[0], params)
        except httpx.HTTPStatusError as e:
            if e.response.status_code == 403 and _reason(e.response) in QUOTA_REASONS:
                self.ledger.flush()
                raise QuotaExhausted(f"QUOTA_EXHAUSTED ({_reason(e.response)})") from None
            raise

    @retry(retry=retry_if_exception(_retryable), stop=stop_after_attempt(5),
           wait=wait_exponential(multiplier=2, max=30), reraise=True)
    def _get(self, resource: str, params: dict[str, Any]) -> dict[str, Any]:
        r = self._http.get(f"{BASE}/{resource}", params=params)
        r.raise_for_status()
        return dict(r.json())

    # ---- helpers -------------------------------------------------------------------------------
    def channels_by_ids(self, ids: list[str]) -> list[dict[str, Any]]:
        out: list[dict[str, Any]] = []
        for batch in chunks(sorted(set(ids))):
            r = self.call("channels.list", part="snippet,contentDetails,statistics,brandingSettings",
                          id=",".join(batch), maxResults=50)
            out.extend(r.get("items", []))
        return out

    def channel_by_handle(self, handle: str) -> dict[str, Any] | None:
        h = handle if handle.startswith("@") else f"@{handle}"
        r = self.call("channels.list", part="snippet,contentDetails,statistics,brandingSettings", forHandle=h)
        items = r.get("items", [])
        return items[0] if items else None

    def channel_by_username(self, username: str) -> dict[str, Any] | None:
        r = self.call("channels.list", part="snippet,contentDetails,statistics,brandingSettings",
                      forUsername=username)
        items = r.get("items", [])
        return items[0] if items else None

    def videos_by_ids(self, ids: list[str]) -> list[dict[str, Any]]:
        out: list[dict[str, Any]] = []
        for batch in chunks(list(dict.fromkeys(ids))):
            r = self.call("videos.list", part="snippet,contentDetails,statistics,status", id=",".join(batch),
                          maxResults=50)
            out.extend(r.get("items", []))
        return out

    def playlist_items(self, playlist_id: str, page_token: str | None = None) -> dict[str, Any]:
        params: dict[str, Any] = {"part": "contentDetails", "playlistId": playlist_id, "maxResults": 50}
        if page_token:
            params["pageToken"] = page_token
        return self.call("playlistItems.list", **params)

    def search(self, **params: Any) -> dict[str, Any]:
        return self.call("search.list", part="snippet", **params)

    def close(self) -> None:
        self.ledger.flush()
        self._http.close()
