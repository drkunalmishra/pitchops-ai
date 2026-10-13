# P2 — Channel Discovery, Entity Resolution and Corpus Harvest · v3 (Free Trial, compressed)

**When:** start Tue 13 Oct night, finish Wed 14 Oct · **Depends on:** P1 acceptance passed

**Why it's urgent:** YouTube allows **10,000 units per day**, resetting at **12:30 IST**. Tonight's quota is unused, and tomorrow brings a fresh 10,000. Two quota-days must yield **≥ 100 accepted channels** and the bulk of the corpus.

## Quota plan

| Run | Window | Units | Purpose |
|---|---|---|---|
| Tonight (Tue) | as soon as P2 is deployed | ~9,000 | Website route (all 3,336 domains, zero quota for fetches) + 40 company searches + 20 keyword sweeps + matcher, then harvest of accepted channels |
| Wed 13:00 IST | Scheduler | ~5,000 | Remaining company searches (T2/T3) + keyword sweeps page 2 |
| Wed 14:30 IST | Scheduler | ~4,000 | Harvest all new channels + metrics |
| Thu 13:00 / 14:30 IST | Scheduler | ~9,000 | Final harvest + metric refresh, then **freeze at 22:00 IST Thu** |

---

## Prompt to paste into Claude Code

````text
You are building Phase P2 of PitchOps AI. Re-read CLAUDE.md (v3) §2 (rules 1, 3, 4, 7, 8, 9), §5 and §7. Time is short: build the simplest working version, deploy, and run it TONIGHT.

GOAL
Discover YouTube channels of DLD-registered Dubai brokers and their companies, resolve each to a company_id or broker_number with an explainable score, harvest all their videos (long-form + Shorts) with daily metric snapshots, compute Tier-1 OPI. Deploy as Cloud Run Jobs + Cloud Scheduler.

HARD TARGET
>= 100 accepted channels linked to a registry company_id or broker_number by end of Wed 14 Oct.

COMPONENTS

1. pitchops/youtube/client.py — httpx wrapper (key from Secret Manager in cloud, .env locally). Every call via QuotaLedger; on quotaExceeded → flush, exit 0 QUOTA_EXHAUSTED. Backoff on 5xx/429. Helpers: channels_by_ids(≤50), channel_by_handle, videos_by_ids(≤50; snippet,contentDetails,statistics,status), playlist_items(playlist_id, page_token).

2. Route A — company websites (no YouTube quota for the fetch) — pitchops/discovery/website_links.py
   - Domains from companies (primary_domain, then other corporate_domains) by broker_count desc.
   - https://{domain}/ then https://www.{domain}/; obey robots.txt; UA "PitchOpsResearchBot/0.1 (+mailto:CONTACT_EMAIL)"; 10s timeout; ≤2 pages/domain (home + one linked contact/about); asyncio concurrency 20; 1s per-host delay. Do not store HTML.
   - Regex: youtube.com/@handle, /channel/UC…, /c/…, /user/…; single-video links → videos.list → channelId only if no channel link. Also capture instagram/linkedin/tiktok URLs into social_links.
   - Resolve via channels.list → channel_candidates (source_route='website').

3. Route B — company search — pitchops/discovery/company_search.py
   - Companies T1 → T2 → T3 by broker_count with no accepted channel: search.list type=channel q="<clean name> Dubai real estate" maxResults=10 regionCode=AE. --searches budget (default 40). Skip already-searched.

4. Route C — keyword sweeps — pitchops/discovery/keyword_sweep.py
   - prompts/keywords_v1.json: "Dubai off plan", "Dubai property investment", "Dubai real estate agent", "Dubai golden visa property", "Dubai apartment tour", "Dubai villa tour", "Dubai property market update", "Dubai real estate Hindi", "Dubai property for Indians", "Dubai real estate Russian", "Business Bay apartment", "Dubai Marina apartment tour", "JVC investment", "Dubai Hills villa", "Palm Jumeirah villa tour", "Emaar off plan", "Damac off plan", "Sobha Hartland", "Dubai rental yield", "Dubai property mistakes".
   - search.list type=channel and type=video (collect channelIds), regionCode=AE, maxResults=50; persist nextPageToken per keyword; --searches budget (default 20).

5. Matcher — pitchops/discovery/matcher.py (pure, unit-tested)
   Signals 0–1 (store all): website_route, domain_match, brn_match (BRN in description == broker_number), name_similarity (rapidfuzz token_set_ratio after stripping LLC/L.L.C/real estate/properties/broker(s)/brokerage/Dubai/UAE), dubai_context, real_estate_context.
   Score: website_route|domain_match|brn_match → 0.95 else 0.55·name + 0.25·dubai + 0.20·real_estate.
   Decision: ≥0.80 auto_accept; 0.60–0.80 review; <0.60 reject. Broker matches need full-name similarity ≥0.90 or brn_match. Portals/aggregators/news → reject unless a registry company.
   MERGE into channel_matches; accepted → MERGE into channels with uploads_playlist_id.

6. Review page (fast manual accept/reject)
   - API: GET /v1/review/channels?decision=review; POST /v1/review/channels/{id} {decision: manual_accept|reject, company_id?, broker_number?}.
   - web /review: table (thumbnail, title, link, candidate company/broker, score, top signals, Accept/Reject). Goal: 50 items in 10 minutes.

7. Harvest — pitchops/harvest/
   - uploads.py: accepted channels with harvest_status new/partial first; page uploads playlist (50/page); checkpoint next_page_token in channels; MAX_VIDEOS_PER_CHANNEL=1000.
   - stats.py: videos.list batches of 50 → MERGE videos; MERGE video_metrics_daily (one row per video per day).
   - shorts.py: is_short = duration ≤180s AND (duration ≤60s OR '#shorts' in title/description/tags); store short_rule. ADR note: API has no Shorts flag.

8. Tier-1 — pitchops/scoring/opi.py (pure + tests): CLAUDE.md §7; cohorts (is_short, duration bucket); creator_median_views from videos older than 7 days; f4 null until comments exist. jobs/score.py writes video_scores.

9. Deploy + schedule
   - One container image; Cloud Run Jobs: discover, harvest, score (sa-jobs, 1 vCPU, 1 GiB, task-timeout 3600s, parallelism 1, max-retries 1).
   - infra/20_scheduler.sh (time zone Asia/Kolkata, invoked by sa-scheduler):
       discover  13:00 daily
       harvest   14:30 and 23:30 daily
       score     17:00 and 00:30 daily
   - Env flag CORPUS_FROZEN=true makes discover/harvest exit immediately (set Thu 22:00 IST).
   - Immediately after deploying: execute discover, then harvest, then score MANUALLY (gcloud run jobs execute … --wait) to use tonight's quota.

10. Dashboard: extend /v1/corpus/stats + tiles: channels by match_type/source_route, review queue size, videos total/shorts/long, quota used today, Gemini spend.

11. Ethics: no comment author fields, no phones/personal emails, robots.txt respected, docs/data-sources.md written.

ACCEPTANCE TESTS (Phase Report with BigQuery counts)
- Unit tests (matcher, quota, OPI, shorts) green; CI guard still passes.
- After tonight + Wed runs: accepted channels ≥ 100 (≥ 60 company matches); each has company_id or broker_number.
- Print 20 random auto_accept rows (title, link, matched entity, score, top signal) for my spot check; target ≥ 18 correct.
- videos ≥ 20,000 with Shorts and long-form present; no duplicate video_id.
- Today's metrics snapshot exists for every harvested video; re-running harvest adds no duplicates.
- quota_ledger today ≤ 9,000. Scheduler jobs listed with next run times.
- Cost line: Cloud Run Jobs + BigQuery usage expected < $2.
````

## Bring back after P2
- The Phase Report and the 20-row spot check.
- Clear the `/review` queue (about 10 minutes).
- Then I'll send **P3 + P4** (Gemini analysis and persona building) for Thursday.
