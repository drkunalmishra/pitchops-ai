import math

from pitchops.personas.aggregate import aggregate, confidence, humanize, video_labels


def vid(i: int, ch: str = "c1", deep: bool = False, fw: list | None = None, personas: list | None = None,
        motive: str = "invest", opi: float = 50, trending: float = 0.0, **kw: object) -> dict:
    base = {"video_id": f"v{i}", "channel_id": ch, "company_id": f"co_{ch}", "deep": deep, "is_short_candidate": True,
            "opi": opi, "trending": trending, "eng_rate": 0.05}
    if deep:
        base.update(frameworks=fw or ["authority"], personas=personas or ["yield_investor"], motive=motive,
                    archetype="property_tour", presenter=True, sales_pressure=3.0, evidence_density=0.5,
                    education_to_sales=1.0, compliance_risk=False)
    else:
        base.update(g_frameworks=fw or ["authority"], g_personas=personas or ["yield_investor"], g_motive=motive,
                    g_archetype="property_tour")
    base.update(kw)
    return base


def test_confidence_formula() -> None:
    assert confidence(99, 5) == 1.0
    assert confidence(9, 1) == round((math.log10(10) / 2) * 0.2, 4)


def test_labels_prefer_deep_and_weights() -> None:
    d = video_labels(vid(1, deep=True, fw=["fomo_scarcity", "financial", "lifestyle"]))
    t = video_labels(vid(2))
    assert d["weight"] == 1.0 and d["seller"] == ["fomo_scarcity", "financial"]
    assert d["format"] == "property_tour|on_camera|short"
    assert t["weight"] == 0.3 and t["format"] == "property_tour|unknown|short" and t["buyer"] == ["yield_investor|invest"]


def test_aggregate_counts_links_and_bands() -> None:
    vids = [vid(i, ch=f"c{i % 6}", deep=i < 10, opi=i, trending=i / 10) for i in range(60)]
    vids += [vid(100 + i, ch=f"c{i % 6}", fw=["lifestyle"], personas=["end_user_family"], motive="settle", opi=5,
                 trending=-1) for i in range(60)]
    out = aggregate(vids)
    p = {r["persona_id"]: r for r in out["personas"]}
    a = p["seller:authority"]
    assert a["video_count"] == 60 and a["deep_videos"] == 10 and a["weighted_evidence"] == round(10 + 50 * 0.3, 2)
    assert a["channel_count"] == 6 and a["confidence"] == round(min(1, math.log10(26) / 2), 4)
    assert p["seller:authority"]["rating_band"] == "A" and p["seller:lifestyle"]["rating_band"] in "BCDE"
    assert any(link["seller_persona_id"] == "seller:lifestyle" and link["buyer_persona_id"] == "buyer:end_user_family|settle"
               for link in out["links"])
    assert len(a["example_video_ids"]) <= 12 and a["example_video_ids"][0] in {f"v{i}" for i in range(10)}


def test_low_confidence_is_insufficient() -> None:
    out = aggregate([vid(1), vid(2)])
    assert all(r["rating_band"] == "insufficient_evidence" for r in out["personas"])


def test_humanize() -> None:
    assert humanize("seller:fomo_scarcity") == "Fomo Scarcity seller"
    assert humanize("buyer:yield_investor|invest") == "Yield Investor (invest)"
    assert humanize("format:property_tour|on_camera|short") == "Property Tour · presenter on camera · short"
