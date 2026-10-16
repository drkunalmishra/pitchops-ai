from collections import Counter

from pitchops.media.plans import budget_check, cost, plan_hash, rotate_avatars, shots

SCRIPT = {"current": {"avatar_intro_line": "Hi", "avatar_outro_line": "Bye", "cta": "Call PitchOps Demo Realty",
                      "narration": [{"text": f"line {i}"} for i in range(6)], "on_screen_facts": [{"text": "From AED 2M"}]}}
IMGS = [{"id": f"i{i}", "gcs": f"gs://b/{i}.jpg", "tag": t, "quality": 0.9, "selected": True}
        for i, t in enumerate(["aerial", "exterior_facade", "interior_living", "pool_amenity", "kitchen", "lobby"])]


def test_budget_guard_blocks_over_cap() -> None:
    assert budget_check(4.0, 100.0, 120.0, 17.0, 200.0) is None
    assert "media budget" in budget_check(4.0, 118.0, 120.0, 17.0, 200.0)
    assert "project cap" in budget_check(4.0, 10.0, 120.0, 190.0, 200.0)
    assert budget_check(2.0, 0.0, 1.0, 0.0, 200.0)  # temporary low cap refuses


def test_avatar_rotation_is_balanced() -> None:
    avs = [f"a{i}" for i in range(8)]
    got = rotate_avatars(["a0"] * 40, avs, 5)
    assert max(Counter(got).values()) == 5 and len(set(got)) == 8


def test_shots_and_cost() -> None:
    s16 = shots(SCRIPT, "16x9", IMGS, 40)
    s9 = shots(SCRIPT, "9x16", IMGS, 40)
    assert [x["kind"] for x in s16][0] == "avatar_intro" and s16[-1]["kind"] == "cta_card"
    assert sum(x["kind"] == "hero_clip" for x in s16) == 2 and sum(x["kind"] == "hero_clip" for x in s9) == 1
    assert cost(s16, 0.15, 0.10) == 4.0 and cost(s9, 0.15, 0.10) == 2.0
    assert plan_hash({"shots": s16}) != plan_hash({"shots": s9})


def test_generator_refuses_unapproved_or_changed_plans() -> None:
    import pytest

    from jobs.media_generate import NotApproved, check_runnable

    shots16 = shots(SCRIPT, "16x9", IMGS, 40)
    plan = {"plan_id": "p", "state": "PREVIEW_READY", "shots": shots16, "property_id": "x", "format": "16x9",
            "script_id": "s", "script_version": 1, "avatar_id": "avatar_in"}
    with pytest.raises(NotApproved):
        check_runnable(plan)
    plan |= {"state": "APPROVED", "approval": {"plan_hash": plan_hash(plan)}}
    check_runnable(plan)  # exact approved plan runs
    plan["avatar_id"] = "avatar_eu"  # edited after approval
    with pytest.raises(NotApproved):
        check_runnable(plan)
