from pitchops.harvest.uploads import video_rows

ITEM = {
    "id": "abcdefghijk",
    "snippet": {"channelId": "UC" + "x" * 22, "title": "Marina tour #shorts", "description": "2BR",
                "publishedAt": "2026-10-01T10:00:00Z", "tags": ["dubai", "shorts"], "defaultAudioLanguage": "en"},
    "contentDetails": {"duration": "PT45S", "caption": "false"},
    "statistics": {"viewCount": "1200", "likeCount": "40"},  # comments disabled -> no commentCount
    "status": {"privacyStatus": "public"},
}


def test_video_rows() -> None:
    vids, mets = video_rows([ITEM], "run1")
    v, m = vids[0], mets[0]
    assert v["video_id"] == "abcdefghijk" and v["duration_sec"] == 45 and v["is_short"] and v["short_rule"] == "le60"
    assert v["default_language"] == "en" and v["has_captions"] is False and v["tags"] == ["dubai", "shorts"]
    assert m["view_count"] == 1200 and m["like_count"] == 40 and m["comment_count"] is None
    assert len(m["snapshot_date"]) == 10
