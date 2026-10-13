import pytest

from jobs.load_registry import build_brokers, build_companies, validate


def test_pii_dropped() -> None:
    raw = [{"name_en": "A", "name_ar": "ا", "broker_number": "1", "office_name_en": "O", "office_name_ar": "و",
            "email": "a@x.test", "phone": "+971000", "email_domain": "X.test", "is_corporate_email": "True",
            "company_key": "o"}]
    b = build_brokers(raw, {"o": "co_1"})
    assert "phone" not in b[0] and "email" not in b[0]
    assert b[0]["email_domain"] == "x.test" and b[0]["is_corporate_email"] is True and b[0]["company_id"] == "co_1"


def test_duplicate_broker_rejected() -> None:
    b = [{"broker_number": "1", "company_id": "c"}, {"broker_number": "1", "company_id": "c"}]
    with pytest.raises(ValueError):
        validate(b, [])


def test_company_domains_split() -> None:
    c = build_companies([{"company_id": "co_1", "company_key": "k", "office_names_en": "E", "office_name_ar": "",
                          "broker_count": "3", "corporate_domains": "a.test|B.test", "primary_domain": "a.test",
                          "discovery_tier": "T4"}])
    assert c[0]["corporate_domains"] == ["a.test", "b.test"] and c[0]["broker_count"] == 3
    assert c[0]["office_name_ar"] is None
