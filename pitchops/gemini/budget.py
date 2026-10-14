"""GeminiBudget — checked before every Gemini call (CLAUDE.md §2 rule 7, D14).

Caps: total (GEMINI_BUDGET_USD), per IST day (GEMINI_DAILY_USD) and optionally per phase (jobs whose name starts
with the phase prefix, e.g. "p3_"). Spend is the *estimate* in llm_calls.cost_usd_est. Thread-safe; the store is
re-read at most every `ttl_s` seconds and spend recorded in between is tracked locally.
"""

from __future__ import annotations

import threading
import time
from collections.abc import Callable
from datetime import UTC, date, datetime
from typing import Protocol
from zoneinfo import ZoneInfo

IST = ZoneInfo("Asia/Kolkata")


class BudgetExhausted(Exception):
    pass


class SpendStore(Protocol):
    def spend(self, day_ist: date, phase_prefix: str | None = None) -> tuple[float, float, float]:
        """Returns (total_usd_all_time, usd_on_day_ist, usd_for_phase)."""
        ...


class GeminiBudget:
    def __init__(self, store: SpendStore, total_cap: float = 60.0, daily_cap: float = 25.0,
                 phase_prefix: str | None = None, phase_cap: float | None = None, ttl_s: float = 0.0,
                 clock: Callable[[], datetime] = lambda: datetime.now(UTC)) -> None:
        self.store, self.total_cap, self.daily_cap, self.clock = store, total_cap, daily_cap, clock
        self.phase_prefix, self.phase_cap, self.ttl_s = phase_prefix, phase_cap, ttl_s
        self.pending = 0.0  # spend recorded locally since the last store read
        self._cache: tuple[float, float, float] | None = None
        self._read_at = 0.0
        self._lock = threading.Lock()

    def status(self) -> dict[str, float]:
        with self._lock:
            if self._cache is None or time.monotonic() - self._read_at >= self.ttl_s:
                self._cache = self.store.spend(self.clock().astimezone(IST).date(), self.phase_prefix)
                self._read_at = time.monotonic()
                if self.ttl_s:
                    self.pending = 0.0  # logged rows are now visible in the store
            total, today, phase = self._cache
            p = self.pending
        return {"total_usd": total + p, "today_usd": today + p, "phase_usd": phase + p,
                "total_cap": self.total_cap, "daily_cap": self.daily_cap, "phase_cap": self.phase_cap or 0.0}

    def check(self, next_call_estimate: float = 0.0) -> None:
        s = self.status()
        if s["total_usd"] + next_call_estimate >= self.total_cap:
            raise BudgetExhausted(f"BUDGET_EXHAUSTED: total ${s['total_usd']:.4f} >= ${self.total_cap}")
        if s["today_usd"] + next_call_estimate >= self.daily_cap:
            raise BudgetExhausted(f"BUDGET_EXHAUSTED: today ${s['today_usd']:.4f} >= ${self.daily_cap}")
        if self.phase_cap and s["phase_usd"] + next_call_estimate >= self.phase_cap:
            raise BudgetExhausted(f"BUDGET_EXHAUSTED: phase {self.phase_prefix} ${s['phase_usd']:.4f} >= ${self.phase_cap}")

    def record(self, usd: float) -> None:
        with self._lock:
            self.pending += usd


class BigQuerySpendStore:
    def spend(self, day_ist: date, phase_prefix: str | None = None) -> tuple[float, float, float]:
        from pitchops.bq import query
        from pitchops.config import get_settings

        rows = query(
            "SELECT COALESCE(SUM(cost_usd_est),0) AS total, "
            "COALESCE(SUM(IF(DATE(ts, 'Asia/Kolkata') = @d, cost_usd_est, 0)),0) AS today, "
            "COALESCE(SUM(IF(STARTS_WITH(job, @p), cost_usd_est, 0)),0) AS phase "
            f"FROM `{get_settings().table('llm_calls')}`", {"d": day_ist.isoformat(), "p": phase_prefix or "\u0000"})
        return float(rows[0]["total"]), float(rows[0]["today"]), float(rows[0]["phase"])
