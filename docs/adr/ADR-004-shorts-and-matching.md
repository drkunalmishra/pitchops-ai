# ADR-004 — Shorts rule and channel matching

**Status:** Accepted · **Date:** 14 Oct 2026

## Shorts
The YouTube Data API has **no Shorts flag**. We classify with a documented rule (`pitchops/harvest/shorts.py`):
`is_short = duration ≤ 180 s AND (duration ≤ 60 s OR '#shorts' in title / description / tags)`, and store the rule
that fired in `videos.short_rule` (`le60`, `le180_hashtag`, `le180_no_hashtag`, `gt180`, `unknown_duration`).
Since Oct 2024 Shorts can be up to 3 minutes, so 61–180 s videos without the hashtag are counted as long-form —
a known, conservative error.

## Channel → registry matching (`pitchops/discovery/matcher.py`)
Signals (all stored in `channel_matches.signals`): `website_route`, `domain_match`, `brn_match`, `name_similarity`
(rapidfuzz `token_sort_ratio` on cleaned names; names < 4 chars must match exactly), `dubai_context`,
`real_estate_context`. Score and thresholds as in P2: strong signal → 0.95, else `0.55·name + 0.25·dubai + 0.20·re`;
≥ 0.80 auto_accept, 0.60–0.80 review, < 0.60 reject.

Precision guards added in P2 (target ≥ 18/20 correct auto-accepts):
1. A **name-only** auto_accept also needs `name_similarity ≥ 0.85`; otherwise it goes to review.
2. Broker matches need a BRN in the description, or a full-name similarity ≥ 0.90 on a name that is **unique** in the registry.
3. Portals, aggregators, news outlets and developers (Bayut, Property Finder, Emaar, Damac, …) are rejected unless a
   strong signal or a near-exact (≥ 0.95) registry company name matches.
4. Human decisions (Firestore `review_decisions`, applied by jobs) are never overwritten by the matcher.
