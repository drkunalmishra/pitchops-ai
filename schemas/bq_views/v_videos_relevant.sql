-- In-window (D2), relevant (D3) videos of relevant channels. Default source for every downstream query.
SELECT v.* FROM `{dataset}.videos` v
JOIN `{dataset}.channels` c USING (channel_id)
WHERE v.in_window AND v.is_relevant AND IFNULL(c.is_relevant, TRUE)
