from datetime import UTC, date, datetime, timedelta

import pytest

from pitchops.youtube.quota import COST, QuotaExhausted, QuotaLedger, day_pt


class FakeStore:
    def __init__(self, used: int = 0) -> None:
        self.rows: list[dict] = []
        self.base = used
        self.reads = 0

    def units_used(self, d: date) -> int:
        self.reads += 1
        return self.base + sum(r["units"] for r in self.rows if r["day_pt"] == d.isoformat())

    def write(self, rows: list[dict]) -> None:
        self.rows.extend(rows)


class Clock:
    def __init__(self, t: datetime) -> None:
        self.t = t

    def __call__(self) -> datetime:
        return self.t


def test_costs() -> None:
    assert COST["search.list"] == 100 and COST["videos.list"] == 1


def test_day_key_is_pacific() -> None:
    # 06:00 UTC on the 14th is still the 13th in Los Angeles
    assert day_pt(datetime(2026, 10, 14, 6, 0, tzinfo=UTC)) == date(2026, 10, 13)
    assert day_pt(datetime(2026, 10, 14, 8, 0, tzinfo=UTC)) == date(2026, 10, 14)


def test_spend_until_cap() -> None:
    store = FakeStore(used=8800)
    q = QuotaLedger(store, "t", "r", cap=9000)
    assert q.can_spend("search.list")
    q.spend("search.list")
    q.spend("search.list")
    assert not q.can_spend("search.list") and not q.can_spend("videos.list")
    with pytest.raises(QuotaExhausted):
        q.spend("videos.list")
    q.flush()
    assert sum(r["units"] for r in store.rows) == 200


def test_unknown_method() -> None:
    with pytest.raises(KeyError):
        QuotaLedger(FakeStore(), "t", "r").can_spend("foo.list")


def test_buffer_and_refresh() -> None:
    store = FakeStore()
    q = QuotaLedger(store, "t", "r", cap=9000)
    for _ in range(60):
        q.spend("videos.list")
    assert q.used_today() == 60
    assert store.reads >= 2  # initial read + refresh after 50 calls
    q.flush()
    assert len(store.rows) == 60


def test_day_rollover_resets() -> None:
    clock = Clock(datetime(2026, 10, 13, 18, 0, tzinfo=UTC))
    store = FakeStore()
    q = QuotaLedger(store, "t", "r", cap=150, clock=clock)
    q.spend("search.list")
    assert not q.can_spend("search.list")
    clock.t += timedelta(days=1)
    assert q.can_spend("search.list")
