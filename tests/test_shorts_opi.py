from datetime import date

from pitchops.harvest.shorts import classify, iso_duration_sec
from pitchops.scoring.opi import cohort_of, percentile, score_videos


def test_iso_duration() -> None:
    assert iso_duration_sec("PT1M5S") == 65 and iso_duration_sec("PT2H") == 7200 and iso_duration_sec("P0D") == 0
    assert iso_duration_sec(None) is None


def test_shorts_rule() -> None:
    assert classify(45, "x", "", []) == (True, "le60")
    assert classify(120, "Tour #shorts", "", []) == (True, "le180_hashtag")
    assert classify(120, "Tour", "", ["shorts"]) == (True, "le180_hashtag")
    assert classify(120, "Tour", "", []) == (False, "le180_no_hashtag")
    assert classify(400, "#shorts", "", []) == (False, "gt180")


def test_cohorts_and_percentile() -> None:
    assert cohort_of(True, 30) == "short|le60" and cohort_of(False, 900) == "long|gt600"
    assert percentile([0, 10], 0.5) == 5


def vid(i: int, views: int | None, likes: int | None = 10, ch: str = "c1", pub: str = "2026-09-01T00:00:00Z") -> dict:
    return {"video_id": f"v{i}", "channel_id": ch, "is_short": True, "duration_sec": 30, "published_at": pub,
            "view_count": views, "like_count": likes, "comment_count": 1}


def test_opi_range_and_order() -> None:
    vids = [vid(i, 100 * (i + 1)) for i in range(40)]
    out = {s["video_id"]: s for s in score_videos(vids, date(2026, 10, 14))}
    assert all(0 <= s["opi"] <= 100 for s in out.values())
    assert out["v39"]["opi"] > out["v0"]["opi"]
    assert out["v0"]["f4"] is None and out["v0"]["opi_confidence"] == 0.85  # f4 weight missing


def test_missing_likes_reduces_confidence() -> None:
    vids = [vid(i, 100 * (i + 1)) for i in range(40)] + [vid(99, 500, likes=None)]
    s = {x["video_id"]: x for x in score_videos(vids, date(2026, 10, 14))}["v99"]
    assert s["f2"] is None and s["opi_confidence"] == 0.6 and s["opi"] is not None


def test_no_views_no_score() -> None:
    s = score_videos([vid(1, None)], date(2026, 10, 14))[0]
    assert s["opi"] is None and s["opi_confidence"] == 0


def test_f4_from_comment_intent() -> None:
    vids = [vid(i, 100 * (i + 1)) for i in range(40)]
    for i, x in enumerate(vids):
        x["intent_rate"] = i / 100
    s = {x["video_id"]: x for x in score_videos(vids, date(2026, 10, 14))}
    assert s["v10"]["f4"] == 0.1 and s["v10"]["opi_confidence"] == 1.0
