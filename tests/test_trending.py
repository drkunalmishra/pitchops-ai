import math

import pytest

from pitchops.scoring.trending import robust_z, trending_scores


def v(i: int, day: int, views: int, likes: int = 0, comments: int = 0, ch: str = "c") -> dict:
    return {"video_id": f"v{i}", "channel_id": ch, "published_at": f"2026-01-{day:02d}T00:00:00Z",
            "view_count": views, "like_count": likes, "comment_count": comments}


def test_robust_z_hand_computed() -> None:
    # median 3, |dev| = [2,1,0,1,7] -> MAD 1
    z = robust_z([1, 2, 3, 4, 10])
    assert z[2] == 0 and z[4] == pytest.approx(7 / 1.4826)


def test_trending_fixture() -> None:
    # 6 videos within 90 days; v5 has 1000 views, others 100. Engagement equal except v5.
    vids = [v(i, i + 1, 100, likes=10) for i in range(5)] + [v(5, 6, 1000, likes=200)]
    out = {r["video_id"]: r for r in trending_scores(vids)}
    r = out["v5"]
    assert r["baseline_kind"] == "window_90d" and r["baseline"] == 100 and r["outlier"] == 10
    # eng: five at 0.10, v5 at 0.20 -> median 0.10, MAD 0 -> z = 0
    assert r["z_eng"] == 0
    assert r["trending"] == pytest.approx(0.65 * math.log2(10))
    # an ordinary video: baseline = median of the other five = 100 -> outlier 1 -> trending 0
    assert out["v0"]["outlier"] == 1 and out["v0"]["trending"] == pytest.approx(0.0)


def test_small_channel_uses_channel_median() -> None:
    out = trending_scores([v(0, 1, 50), v(1, 2, 150), v(2, 3, 100)])
    assert all(r["baseline_kind"] == "channel_median" and r["baseline"] == 100 for r in out)


def test_z_clamped_and_outlier_floor() -> None:
    vids = [v(i, i + 1, 100, likes=i) for i in range(6)] + [v(9, 8, 0, likes=0)]
    r = {x["video_id"]: x for x in trending_scores(vids)}["v9"]
    assert r["outlier"] == 0 and r["trending"] >= 0.65 * math.log2(0.01) - 0.35 * 3
