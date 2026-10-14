-- Admin / QA only: flagged rows, never used by analysis.
SELECT v.video_id, v.channel_id, v.title, v.relevance_reason, v.relevance_source, c.is_relevant AS channel_relevant
FROM `{dataset}.videos` v JOIN `{dataset}.channels` c USING (channel_id)
WHERE v.in_window AND (v.is_relevant = FALSE OR c.is_relevant = FALSE)
