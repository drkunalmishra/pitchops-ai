"""QuotaLedger — every YouTube Data API call is metered here (CLAUDE.md §2 rule 8).

The YouTube quota day follows America/Los_Angeles midnight (= 12:30/13:30 IST).
"""

from __future__ import annotations

from collections.abc import Callable
from datetime import UTC, date, datetime
from typing import Any, Protocol
from zoneinfo import ZoneInfo

COST: dict[str, int] = {
    "search.list": 100,
    "channels.list": 1,
    "playlistItems.list": 1,
    "videos.list": 1,
    "commentThreads.list": 1,
}
PT = ZoneInfo("America/Los_Angeles")
REFRESH_EVERY = 50
FLUSH_EVERY = 25


class QuotaExhausted(Exception):
    pass


class QuotaStore(Protocol):
    def units_used(self, day_pt: date) -> int: ...
    def write(self, rows: list[dict[str, Any]]) -> None: ...


def day_pt(now: datetime | None = None) -> date:
    return (now or datetime.now(UTC)).astimezone(PT).date()


class QuotaLedger:
    def __init__(self, store: QuotaStore, job: str, run_id: str, cap: int = 9000,
                 clock: Callable[[], datetime] = lambda: datetime.now(UTC)) -> None:
        self.store, self.job, self.run_id, self.cap, self.clock = store, job, run_id, cap, clock
        self._day: date | None = None
        self._used_cached = 0
        self._since_refresh = REFRESH_EVERY  # force a read on first use
        self._buffer: list[dict[str, Any]] = []

    @staticmethod
    def cost(method: str) -> int:
        if method not in COST:
            raise KeyError(f"unknown YouTube method {method!r}; add it to COST")
        return COST[method]

    def _sync(self) -> None:
        today = day_pt(self.clock())
        if today != self._day:
            self.flush()
            self._day, self._since_refresh = today, REFRESH_EVERY
        if self._since_refresh >= REFRESH_EVERY:
            self.flush()
            self._used_cached = self.store.units_used(today)
            self._since_refresh = 0

    def used_today(self) -> int:
        self._sync()
        return self._used_cached + sum(r["units"] for r in self._buffer)

    def remaining(self) -> int:
        return max(0, self.cap - self.used_today())

    def can_spend(self, method: str) -> bool:
        return self.used_today() + self.cost(method) <= self.cap

    def spend(self, method: str) -> None:
        """Record one call. Call can_spend() first; spend() raises if it would cross the cap."""
        units = self.cost(method)
        if not self.can_spend(method):
            raise QuotaExhausted(f"QUOTA_EXHAUSTED: {self.used_today()}+{units} > {self.cap}")
        now = self.clock()
        self._buffer.append({"ts": now.isoformat(), "day_pt": day_pt(now).isoformat(), "method": method,
                             "units": units, "job": self.job, "run_id": self.run_id,
                             "ingested_at": now.isoformat()})
        self._since_refresh += 1
        if len(self._buffer) >= FLUSH_EVERY:
            self.flush()

    def flush(self) -> None:
        if not self._buffer:
            return
        rows, self._buffer = self._buffer, []
        self.store.write(rows)
        self._used_cached += sum(r["units"] for r in rows)


class BigQueryQuotaStore:
    def units_used(self, day: date) -> int:
        from pitchops.bq import query
        from pitchops.config import get_settings

        rows = query(f"SELECT COALESCE(SUM(units),0) AS u FROM `{get_settings().table('quota_ledger')}` "
                     "WHERE day_pt = @d", {"d": day.isoformat()})
        return int(rows[0]["u"])

    def write(self, rows: list[dict[str, Any]]) -> None:
        from pitchops.bq import insert_rows

        insert_rows("quota_ledger", rows)
