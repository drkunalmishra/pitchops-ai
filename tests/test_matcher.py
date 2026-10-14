from pitchops.discovery.matcher import Registry, domains_in, match_channel
from pitchops.discovery.names import clean, company_names

REG = Registry.from_rows(
    [{"company_id": "co_1", "office_names_en": "DRIVEN PROPERTIES L.L.C | DRIVEN PROPERTIES LLC (BRANCH)",
      "primary_domain": "drivenproperties.com", "corporate_domains": ["drivenproperties.com"], "broker_count": 500},
     {"company_id": "co_2", "office_names_en": "F A M REAL ESTATE BROKER L.L.C", "primary_domain": "famproperties.com",
      "corporate_domains": [], "broker_count": 400},
     {"company_id": "co_3", "office_names_en": "HOME REAL ESTATE BROKER", "primary_domain": None,
      "corporate_domains": ["gmail.com"], "broker_count": 3},
     {"company_id": "co_4", "office_names_en": "CLASSIC PROPERTIES REAL ESTATE L.L.C", "primary_domain": None,
      "corporate_domains": [], "broker_count": 3},
     {"company_id": "co_5", "office_names_en": "EXCLUSIVE LINKS REAL ESTATE BROKERS L.L.C", "primary_domain": None,
      "corporate_domains": [], "broker_count": 90}],
    [{"broker_number": "12345", "name_en": "Andrada Ion", "company_id": "co_1"},
     {"broker_number": "22222", "name_en": "Mohammed Ali", "company_id": "co_2"},
     {"broker_number": "33333", "name_en": "Mohammed Ali", "company_id": "co_3"}])


def ch(title: str, desc: str = "", handle: str = "", country: str | None = None) -> dict:
    return {"channel_id": "UCx", "title": title, "description": desc, "handle": handle, "country": country}


def test_clean() -> None:
    assert clean("F A M REAL ESTATE BROKER L.L.C (BRANCH)") == "fam"
    assert company_names("DRIVEN PROPERTIES L.L.C | DRIVEN PROPERTIES LLC") == ["driven"]


def test_website_route_is_strong() -> None:
    web = [{"source_route": "website", "company_id_guess": "co_2"}]
    m = match_channel(ch("Some Channel", "Luxury villas for sale"), web, REG)
    assert m["decision"] == "auto_accept" and m["company_id"] == "co_2" and m["match_score"] == 0.95


def test_website_route_without_context_goes_to_review() -> None:
    web = [{"source_route": "website", "company_id_guess": "co_2"}]
    m = match_channel(ch("Jazz and Blues Experience", "live music in Dubai"), web, REG)
    assert m["decision"] == "review" and m["company_id"] == "co_2"
    assert match_channel(ch("Jazz and Blues Experience", "live music"), web, REG)["decision"] == "reject"


def test_generic_short_name_no_match() -> None:
    m = match_channel(ch("Pro-Realty Dubai", "apartments"), [{"source_route": "keyword_sweep"}], REG)
    assert m["decision"] == "reject"


def test_domain_match() -> None:
    m = match_channel(ch("Luxury Tours", "Visit https://www.drivenproperties.com for listings"),
                      [{"source_route": "keyword_sweep"}], REG)
    assert m["signals"]["domain_match"] == 1.0 and m["company_id"] == "co_1" and m["decision"] == "auto_accept"


def test_freemail_domain_ignored() -> None:
    assert domains_in("mail me at x@gmail.com or see youtube.com") == set()


def test_brn_match() -> None:
    m = match_channel(ch("Dubai homes with A", "Broker BRN: 12345"), [{"source_route": "keyword_sweep"}], REG)
    assert m["broker_number"] == "12345" and m["decision"] == "auto_accept"


def test_name_match_company() -> None:
    m = match_channel(ch("Driven Properties | Dubai Real Estate"), [{"source_route": "company_search",
                                                                   "company_id_guess": "co_1"}], REG)
    assert m["company_id"] == "co_1" and m["match_type"] == "company_name" and m["decision"] == "auto_accept"


def test_unrelated_rejected() -> None:
    m = match_channel(ch("Cooking with Sara", "recipes"), [{"source_route": "keyword_sweep"}], REG)
    assert m["decision"] == "reject"


def test_short_name_needs_exact() -> None:
    # "home" cleans to "" (stop word) -> no fuzzy hit on a generic word
    m = match_channel(ch("Homes Dubai", "real estate"), [{"source_route": "keyword_sweep"}], REG)
    assert m["decision"] == "reject"


def test_broker_full_name_unique() -> None:
    m = match_channel(ch("Andrada Ion | Dubai Real Estate", "luxury apartments"), [{"source_route": "keyword_sweep"}],
                      REG)
    assert m["broker_number"] == "12345" and m["match_type"] == "broker_name" and m["decision"] == "auto_accept"


def test_ambiguous_broker_name_not_matched() -> None:
    m = match_channel(ch("Mohammed Ali", "Dubai property"), [{"source_route": "keyword_sweep"}], REG)
    assert m["broker_number"] is None


def test_portal_rejected() -> None:
    m = match_channel(ch("Bayut", "Dubai property portal real estate"), [{"source_route": "keyword_sweep"}], REG)
    assert m["decision"] == "reject"


def test_generic_one_word_name_goes_to_review() -> None:
    m = match_channel(ch("Dubai Classic Estate", "villas"), [{"source_route": "keyword_sweep"}], REG)
    assert m["company_id"] == "co_4" and m["decision"] == "review"


def test_website_of_other_company_prefers_name() -> None:
    m = match_channel(ch("Exclusive Links Real Estate Brokers", "Dubai apartments"),
                      [{"source_route": "website", "company_id_guess": "co_2"}], REG)
    assert m["company_id"] == "co_5" and m["match_type"] == "company_name"
