from datetime import datetime

from pitchops.properties.normalize import (
    build_canonicals,
    canonical_key,
    developer_key,
    is_uae,
    rank_properties,
    select_media,
)


def m(name: str, vid: str, dev: str | None = "DAMAC Properties", area: str | None = None,
      emirate: str | None = "Dubai", price: str | None = None) -> dict:
    return {"project_name": name, "developer": dev, "area": area, "emirate": emirate, "video_id": vid,
            "price_text": price, "property_type": "villa"}


def test_keys() -> None:
    assert canonical_key("The Valley by Emaar") == "valley"
    assert canonical_key("Dubai Islands") == "dubai islands"
    assert canonical_key("Marriott Residence, Dubai") == "marriott residences"
    assert canonical_key("Villa") is None
    assert developer_key("DAMAC Properties") == "damac" and developer_key("Sobha Realty") == "sobha"
    assert is_uae("Dubai") and is_uae(None) and not is_uae("London")


def test_merge_variants_but_not_phases() -> None:
    ms = [m("DAMAC Islands", "a"), m("Damac Islands", "b"), m("DAMAC ISLANDS by Damac", "c"),
          m("DAMAC Islands 2", "d"), m("Damac Islands 2", "e")]
    canon, mapping = build_canonicals(ms)
    assert mapping["damac islands"] == mapping["damac islands"] and len(canon) == 2
    assert mapping["damac islands 2"] != mapping["damac islands"]


def test_different_developers_do_not_merge() -> None:
    canon, mapping = build_canonicals([m("Sobha One", "a", dev="Sobha"), m("Sobha Ones", "b", dev="Emaar")])
    assert len(canon) == 2


def test_overrides_and_non_uae() -> None:
    canon, mapping = build_canonicals([m("Palm Jebel Ali", "a"), m("PJA", "b"), m("Lakeside", "c", emirate="London")],
                                      overrides={"PJA": "Palm Jebel Ali"})
    assert mapping["pja"] == "palm jebel ali" and "lakeside" not in mapping


def test_rank_and_media() -> None:
    now = datetime(2026, 10, 15)
    vids = {f"v{i}": {"channel_id": f"c{i % 3}", "company_id": f"co{i % 3}", "views": 1000 * i,
                      "published_at": datetime(2026, 9, 1), "deep": False, "personas": ["yield_investor"],
                      "frameworks": ["financial"]} for i in range(30)}
    ms = [m("Alpha Tower", f"v{i}") for i in range(10)] + [m("Beta Heights", f"v{i}") for i in range(10, 14)] \
        + [m("Palm Jumeirah", f"v{i}", area="Palm Jumeirah") for i in range(14, 30)] + [m("Gamma", "v1")]
    canon, mapping = build_canonicals(ms)
    rows = rank_properties(canon, mapping, ms, vids, now)
    names = [r["canonical_name"] for r in rows]
    assert "Gamma" not in names  # < 3 videos
    palm = next(r for r in rows if r["canonical_name"] == "Palm Jumeirah")
    assert palm["kind"] == "community" and palm["recent_videos"] == 16 and palm["weighted_videos"] == 24
    select_media(rows, n=2)
    assert palm["media_candidate"] is None
    assert sorted(r["media_candidate"] for r in rows if r["media_candidate"]) == ["short", "walkthrough"]
