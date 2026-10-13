from datetime import date

import pytest

from pitchops.config import Settings
from pitchops.gemini.budget import BudgetExhausted, GeminiBudget
from pitchops.gemini.client import estimate_cost


class FakeSpend:
    def __init__(self, total: float, today: float) -> None:
        self.total, self.today = total, today

    def spend(self, day_ist: date) -> tuple[float, float]:
        return self.total, self.today


def test_under_budget_ok() -> None:
    GeminiBudget(FakeSpend(10, 5), 60, 25).check()


def test_total_cap() -> None:
    with pytest.raises(BudgetExhausted, match="total"):
        GeminiBudget(FakeSpend(60, 1), 60, 25).check()


def test_daily_cap() -> None:
    with pytest.raises(BudgetExhausted, match="today"):
        GeminiBudget(FakeSpend(30, 25.0), 60, 25).check()


def test_pending_counts() -> None:
    b = GeminiBudget(FakeSpend(59.5, 1), 60, 25)
    b.check()
    b.record(0.6)
    with pytest.raises(BudgetExhausted):
        b.check()


def test_next_call_estimate() -> None:
    with pytest.raises(BudgetExhausted):
        GeminiBudget(FakeSpend(59.99, 0), 60, 25).check(next_call_estimate=0.02)


def test_cost_estimate_families() -> None:
    s = Settings(gcp_project_id="x", _env_file=None)
    assert estimate_cost(s, "gemini-3.8-flash", 1_000_000, 0) == 0.5
    assert estimate_cost(s, "gemini-3.5-flash-lite", 1_000_000, 1_000_000) == 0.5
    s2 = Settings(gcp_project_id="x", price_per_mtok_json='{"m": [1, 2]}', _env_file=None)
    assert estimate_cost(s2, "m", 1_000_000, 1_000_000) == 3.0
