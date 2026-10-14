from pitchops.analysis.deep_video import clips_for, derived_metrics, normalize_mmss, validate


def data(segs: list, claims: list | None = None, frameworks: list | None = None, hook: str = "question",
         cta: str = "none") -> dict:
    return {"overview": {"sales_frameworks": frameworks or [], "hook_type": hook, "cta_type": cta, "hook_end_sec": 3},
            "segments": segs, "claims": claims or [], "property_mentions": []}


def seg(a: float, b: float, mode: str = "pitch") -> dict:
    return {"start_sec": a, "end_sec": b, "segment_type": "other", "mode": mode, "summary": "", "on_screen_text": None}


def claim(ts: float, src: bool = False, risky: bool = False, quote: str = "8% ROI") -> dict:
    return {"ts_sec": ts, "quote": quote, "claim_type": "roi_yield", "has_source": src, "source_text": None,
            "is_risky": risky, "risk_note": None}


def test_clips() -> None:
    assert clips_for(45) == ("full", [(0, 45)])
    assert clips_for(300) == ("full", [(0, 300)])
    assert clips_for(600) == ("partial", [(0, 120), (270, 330), (480, 600)])


def test_validate_full_ok_and_coverage() -> None:
    assert validate(data([seg(0, 20), seg(20, 40)]), 40, "full", [(0, 40)]) == []
    errs = validate(data([seg(0, 10)]), 40, "full", [(0, 40)])
    assert any("80%" in e for e in errs)


def test_validate_order_and_bounds() -> None:
    errs = validate(data([seg(0, 30), seg(10, 50)], [claim(99)]), 40, "full", [(0, 40)])
    assert any("overlaps" in e for e in errs) and any("beyond" in e for e in errs)
    assert any("no quote" in e for e in validate(data([seg(0, 40)], [claim(1, quote=" ")]), 40, "full", [(0, 40)]))


def test_validate_partial_clips() -> None:
    clips = [(0, 120), (270, 330), (480, 600)]
    assert validate(data([seg(0, 120), seg(270, 330), seg(480, 600)]), 600, "partial", clips) == []
    assert any("outside" in e for e in validate(data([seg(150, 200)]), 600, "partial", clips))


def test_derived_metrics() -> None:
    d = data([seg(0, 30, "education"), seg(30, 60, "pitch")], [claim(5, src=True), claim(40, risky=True)],
             frameworks=["fomo_scarcity"], hook="bold_claim", cta="contact_call_whatsapp")
    m = derived_metrics(d, 60)
    assert m["pitch_share"] == 0.5 and m["education_to_sales"] == 1.0
    assert m["sourced_claim_share"] == 0.5 and m["evidence_density"] == 1.0
    # 0.35*0.5 + 0.25 + 0.20*0.5 + 0.10 + 0.10 = 0.725
    assert m["sales_pressure_score"] == 7.25 and m["verification_status"] == "unverified_claims"


def test_derived_no_claims() -> None:
    m = derived_metrics(data([seg(0, 10, "neutral")]), 10)
    assert m["sourced_claim_share"] is None and m["verification_status"] == "no_claims" and m["sales_pressure_score"] == 0


def test_normalize_mmss() -> None:
    d = data([seg(0, 45), seg(45, 130), seg(130, 208)], [claim(115)])  # model wrote 1:30 as 130, 2:08 as 208
    assert normalize_mmss(d, 128) is True
    assert [s["end_sec"] for s in d["segments"]] == [45, 90, 128] and d["claims"][0]["ts_sec"] == 75
    assert validate(d, 128, "full", [(0, 128)]) == []


def test_normalize_mmss_leaves_valid_and_ambiguous_alone() -> None:
    ok = data([seg(0, 60), seg(60, 120)])
    assert normalize_mmss(ok, 120) is False and ok["segments"][1]["end_sec"] == 120
    bad = data([seg(0, 175)])  # 175 has '75' seconds -> not MMSS -> no conversion
    assert normalize_mmss(bad, 100) is False
