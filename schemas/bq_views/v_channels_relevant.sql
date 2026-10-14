-- Accepted channels that are relevant (D3/D9). Default source for every downstream query.
SELECT * FROM `{dataset}.channels` WHERE IFNULL(is_relevant, TRUE)
