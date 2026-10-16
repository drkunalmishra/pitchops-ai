from pitchops.personas.naming import validate as validate_naming
from pitchops.reports.company import cited_ids
from pitchops.reports.company import validate as validate_report


def cited(*ids: str) -> dict:
    return {"text": "x", "video_ids": list(ids)}


def test_naming_rejects_uncited_and_unknown_ids() -> None:
    ok = {"description_video_ids": ["a"], "typical_hooks": [cited("a")], "typical_ctas": [cited("b")],
          "what_works": [cited("a")], "what_to_avoid": [cited("b")]}
    assert validate_naming(ok, {"a", "b"}) == []
    bad = {**ok, "what_works": [cited()], "typical_ctas": [cited("zzz")]}
    errs = validate_naming(bad, {"a", "b"})
    assert any("cites no video_id" in e for e in errs) and any("zzz" in e for e in errs)


def test_report_every_statement_cited() -> None:
    funnel = {k: cited("a") for k in ("awareness", "consideration", "decision")}
    d = {"headline": "h", "persona_statement": cited("a"), "funnel": funnel,
         "strengths": [cited("a")], "gaps": [cited("b")], "opportunities": [cited("a", "b")]}
    assert validate_report(d, {"a", "b"}) == [] and cited_ids(d) == ["a", "b"]
    d["gaps"] = [cited("nope")]
    assert validate_report(d, {"a", "b"})
