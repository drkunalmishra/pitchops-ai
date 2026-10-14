# Data sources and collection ethics

| Source | What we collect | How | Stored where |
|---|---|---|---|
| DLD broker registry (local `inputs/`) | name EN/AR, broker number, office EN/AR, **email domain**, `is_corporate_email` | `jobs/load_registry.py` (phone + full email dropped in code) | BigQuery `brokers`, `companies` |
| Registry company websites | Only links: YouTube channel/handle/video URLs and Instagram / LinkedIn company / TikTok URLs. **No HTML is stored.** | `pitchops/discovery/website_links.py` | BigQuery `website_probes` |
| YouTube Data API v3 | Channel metadata + statistics; video metadata + statistics; daily metric snapshots | `pitchops/youtube/client.py` via `QuotaLedger` | BigQuery `channels`, `videos`, `video_metrics_daily` |
| Vertex AI Gemini (P3+) | Derived analysis JSON from public YouTube URLs (no downloads) | `pitchops/gemini/client.py` | BigQuery analysis tables |

## Website crawling rules
- Identifies itself: `PitchOpsResearchBot/0.1 (+mailto:<contact email>)`.
- Obeys `robots.txt` (401/403 on robots.txt = disallow all). Robots-blocked domains are recorded as `robots_allowed=false` and never fetched.
- At most **2 pages per domain** (home + one same-host contact/about page), 10 s timeout, ≤ 2 MB read, **1 s delay per host**, 20 hosts in parallel.
- Free-mail domains that appear in the registry's corporate-domain column (gmail, yahoo, live, …) are skipped.

## YouTube rules
- Only the official Data API v3 with an API key restricted to that API. **No downloading and no youtube.com scraping.**
- Every call is metered by `QuotaLedger` (cap 9,000 units per Pacific day; `quotaExceeded` stops the job cleanly with `QUOTA_EXHAUSTED`).
- Comment samples (later phases) store text and like counts only — **no author names, IDs or avatars**.

## People
- Personas are aggregated patterns; no individual broker is profiled, ranked or cloned.
- A channel may be linked to a `broker_number` only on a BRN printed in the channel description or a **unique** full-name match (≥ 0.90) with Dubai + real-estate context; otherwise it is linked to a company or not at all.
- No phone numbers or personal email addresses are collected from websites or YouTube.
