# P5 — Intelligence Explorer UI + FinOps Dashboard

**When:** Fri 16 Oct morning · **Depends on:** P4 · **Budget:** ~$0 (reads the Firestore read-model; no Gemini calls)

````text
You are building Phase P5 of PitchOps AI. Read CLAUDE.md (§11 D1–D21). The web app (Next.js static export on Firebase Hosting, Firebase Auth, /api/** → Cloud Run api) already exists from P1/P2. Reuse its theme (deep navy + teal, Inter). Use the frontend-design approach: a clean, professional, data-dense UI — no lorem ipsum, real data only. All pages read only relevant data (is_relevant=true).

PAGES
1. Home / Overview: corpus funnel (DLD brokers 33.5k → companies 9.8k → channels 1,108 → relevant channels → videos → relevant last-24-month videos → deep-analysed → comments), key insights cards (top seller persona, top buyer persona, most-discussed property, avg sales pressure), last data refresh, FinOps mini-tile.
2. Persona Explorer:
   - Three tabs: Seller personas · Buyer personas · Formats; each card shows name, description, rating band + confidence, evidence count, key metrics, "what works / avoid".
   - Persona Matrix: seller × buyer heatmap (cell = median trending or video count, toggle), click → link detail with top evidence videos (YouTube thumbnail + timestamped claims + link out to YouTube), typical hooks/CTAs, objections and questions from comments.
3. Property Intelligence: ranked table (top 60) with mentions, companies, views, recency, top buyer personas, common claims; property detail page with evidence videos and the media-candidate flag (16:9 / Short).
4. Companies: searchable table of relevant companies (report type full/light, videos analysed, avg sales pressure, top persona); company page renders the report Markdown (four tables, funnel, persona statement, gaps, evidence links).
5. Video detail: four analysis tables, segment timeline, claims with timestamps, derived metrics, audience summary (or "comments unavailable"), relevance flag.
6. FinOps dashboard (D14): spend by day, by phase, by provider (Vertex Gemini, YouTube quota units, Veo, Imagen, TTS, Cloud Run, BigQuery), bars vs phase caps; cumulative vs TOTAL_PROJECT_CAP_USD $200 and the $300 trial line; YouTube quota usage per day; cost per analysed video, per report, per script, per rendered second; projection for remaining phases. Data from Firestore finops/current (written by jobs/finops_report.py) — add a scheduled run every 3 hours via Cloud Scheduler.
7. Admin/QA (admin role only): irrelevant videos/channels with reasons and a "mark relevant" override (writes relevance_source='manual'); needs_review analyses list.

API: add read endpoints on Cloud Run api only where Firestore read-model is insufficient (e.g., paginated video search from BigQuery with cached results). Every endpoint verifies Firebase token; cap BigQuery bytes per query (maximum_bytes_billed = 1 GB).

ACCEPTANCE
- All pages load with real data on <project>.web.app in under 3 s (cached), work at 1280 px and on mobile width for viewing.
- Persona Matrix click-through shows evidence videos with timestamps.
- FinOps dashboard numbers match finops_report.py output.
- Lighthouse accessibility ≥ 85 on Home and Persona Explorer.
````
