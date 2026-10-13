"""GeminiBudget — checked before every Gemini call (CLAUDE.md §2 rule 7).

Spend is the *estimate* in llm_calls.cost_usd_est. The budget day is the IST calendar day.
"""

from __future__ import annotations

from collections.abc import Callable
from datetime import UTC, date, datetime
from typing import Protocol
from zoneinfo import ZoneInfo

IST = ZoneInfo("Asia/Kolkata")


class BudgetExhausted(Exception):
    pass


class SpendStore(Protocol):
    def spend(self, day_ist: date) -> tuple[float, float]:
        """Returns (total_usd_all_time, usd_on_day_ist)."""
        ...


class GeminiBudget:
    def __init__(self, store: SpendStore, total_cap: float = 60.0, daily_cap: float = 25.0,
                 clock: Callable[[], datetime] = lambda: datetime.now(UTC)) -> None:
        self.store, self.total_cap, self.daily_cap, self.clock = store, total_cap, daily_cap, clock
        self.pending = 0.0  # spend recorded locally since the last store read (not yet visible)

    def status(self) -> dict[str, float]:
        total, today = self.store.spend(self.clock().astimezone(IST).date())
        return {"total_usd": total + self.pending, "today_usd": today + self.pending,
                "total_cap": self.total_cap, "daily_cap": self.daily_cap}

    def check(self, next_call_estimate: float = 0.0) -> None:
        s = self.status()
        if s["total_usd"] + next_call_estimate >= self.total_cap:
            raise BudgetExhausted(f"BUDGET_EXHAUSTED: total ${s['total_usd']:.4f} >= ${self.total_cap}")
        if s["today_usd"] + next_call_estimate >= self.daily_cap:
            raise BudgetExhausted(f"BUDGET_EXHAUSTED: today ${s['today_usd']:.4f} >= ${self.daily_cap}")

    def record(self, usd: float) -> None:
        self.pending += usd


class BigQuerySpendStore:
    def spend(self, day_ist: date) -> tuple[float, float]:
        from pitchops.bq import query
        from pitchops.config import get_settings

        rows = query(
            "SELECT COALESCE(SUM(cost_usd_est),0) AS total, "
            "COALESCE(SUM(IF(DATE(ts, 'Asia/Kolkata') = @d, cost_usd_est, 0)),0) AS today "
            f"FROM `{get_settings().table('llm_calls')}`", {"d": day_ist.isoformat()})
        return float(rows[0]["total"]), float(rows[0]["today"])
