from datetime import date

from pitchops.workflow.compliance import check

FACTS = {
    "f1": {"field": "developer", "value": "Emaar"},
    "f2": {"field": "project", "value": "The Valley"},
    "f3": {"field": "location", "value": "Dubai-Al Ain Road"},
    "f4": {"field": "starting price", "value": "AED 1.9M", "expires_at": "2026-12-31"},
    "old": {"field": "payment plan", "value": "80/20", "expires_at": "2025-01-01"},
}


def script(**kw) -> dict:
    base = {"hook": "Looking for space for your family?", "permit": "DEMO-PERMIT",
            "narration": [{"text": "A community by Emaar.", "fact_ids": ["f1", "f2", "f3"]},
                          {"text": "Townhouses from AED 1.9M.", "fact_ids": ["f4"]}],
            "cta": {"text": "Book a viewing with PitchOps Demo Realty."}, "similarity_to_sources": 0.1}
    return base | kw


def test_clean_script_passes() -> None:
    r = check(script(), FACTS, today=date(2026, 10, 16))
    assert r["status"] == "PASS", r["findings"]


def test_guaranteed_return_blocks() -> None:
    s = script(narration=[{"text": "Guaranteed 12% returns every year.", "fact_ids": ["f1", "f2", "f3"]}])
    r = check(s, FACTS, today=date(2026, 10, 16))
    assert r["status"] == "BLOCK" and any(f["rule_id"] == "UAE-CLAIM-002" for f in r["findings"])


def test_number_without_fact_blocks_and_expired_fact_blocks() -> None:
    s = script(narration=[{"text": "Only 5% down payment.", "fact_ids": []},
                          {"text": "80/20 plan.", "fact_ids": ["old"]}])
    rules = {f["rule_id"] for f in check(s, FACTS, today=date(2026, 10, 16))["findings"]}
    assert {"UAE-FACT-001", "UAE-EXPIRY-006"} <= rules


def test_missing_permit_and_cta_warn() -> None:
    r = check(script(permit="", cta={"text": "Thanks for watching"}), FACTS, today=date(2026, 10, 16))
    assert r["status"] == "WARN"
    assert {f["rule_id"] for f in r["findings"]} >= {"UAE-PERMIT-003", "CTA-010"}


def test_similarity() -> None:
    assert check(script(similarity_to_sources=0.9), FACTS, today=date(2026, 10, 16))["status"] == "BLOCK"


def test_spelled_out_numbers_need_facts() -> None:
    s = script(narration=[{"text": "Prices start from around nineteen million dirhams.", "fact_ids": []},
                          {"text": "A community by Emaar.", "fact_ids": ["f1", "f2", "f3"]}])
    assert any(f["rule_id"] == "UAE-FACT-001" for f in check(s, FACTS, today=date(2026, 10, 16))["findings"])
    ok = script(narration=[{"text": "Spacious homes for growing families.", "fact_ids": []},
                           {"text": "A community by Emaar.", "fact_ids": ["f1", "f2", "f3"]}])
    assert check(ok, FACTS, today=date(2026, 10, 16))["status"] == "PASS"
