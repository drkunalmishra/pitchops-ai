from pitchops.analysis.relevance_rules import rule_irrelevant


def test_non_uae_market() -> None:
    assert rule_irrelevant("3BHK flats in Pune for sale", "Hinjewadi", []) == "rule:non_uae_market:pune"


def test_non_uae_but_dubai_mentioned_is_not_flagged() -> None:
    assert rule_irrelevant("London vs Dubai: where to invest?", "", []) is None


def test_team_culture() -> None:
    assert rule_irrelevant("Our team birthday celebration 🎉", "fun at the office", ["team"]) == \
        "rule:team_culture:birthday"


def test_team_with_property_content_goes_to_gemini() -> None:
    assert rule_irrelevant("We are hiring! Join our team", "Dubai real estate agents wanted", []) is None


def test_plain_property_video() -> None:
    assert rule_irrelevant("2BR apartment tour in Dubai Marina", "", []) is None
