# PitchOps AI — Submission pack (AI Builder Cup 2026)

| Item | Value |
|---|---|
| Deployed prototype | https://pitchops-ai-2026.web.app (sign in with the demo account given in the submission form) |
| GitHub repository | https://github.com/drkunalmishra/pitchops-ai |
| Theme | Future of Work & Enterprise Productivity |

## Brief description

**PitchOps AI turns the public sales videos of Dubai's real-estate brokers into an evidence-rated persona playbook,
then uses that playbook to produce compliant, on-brand sales pitches — scripts and finished avatar videos — in
minutes instead of days.**

We started from the Dubai Land Department register (33,565 brokers, 9,862 companies). From it we matched 1,141
YouTube channels and harvested 227,483 videos through the YouTube Data API. All analysis is restricted to relevant
UAE real-estate content from the last 24 months (68,940 videos). Gemini text-tagged 106k videos. It then watched
493 top-trending videos directly from their YouTube URLs, with nothing downloaded, and extracted hooks, sales
tactics, target buyers, claims and compliance risks with timestamped evidence. We also classified 16,271 comments
for buying intent. The result is a Persona Database of 139 seller, buyer and format personas and 4,206 rated links
between them, plus reports for 386 companies and a ranking of 2,375 properties.

Next comes the Pitch Workflow. Script Studio generates grounded scripts, 111 so far, for a chosen property and
buyer persona, and checks each one against UAE advertising rules: no guaranteed returns, sourced yield figures and
a permit placeholder. Gemini explains every flag and can rewrite a single line. A human then approves the script,
and the approval is a frozen, audited record. The Media Studio turns each approved script into a video plan with a
cost estimate. After the owner approves the plan, Veo animates one of 8 fictional presenter avatars and the
property photos, Cloud TTS narrates, and Lyria adds music. Sixteen finished videos are in the app. A FinOps
dashboard tracks every paid call against hard budget caps.

**How we use Google's stack:**
- **Gemini (Vertex AI)**
  - **Gemini Flash** analyses video straight from the YouTube URL.
  - **Gemini Flash-Lite** does the bulk text tagging.
  - **Gemini** also names the personas and writes the company reports, scripts and compliance explanations.
  - **The Gemini image model** draws the avatar portraits.
  - **Veo 3.1** and **Lyria** generate the presenter, property clips and music.
  - Every output is checked against a JSON schema before it is stored.
- **Cloud Run:** a FastAPI service powers the explorer, studio, media and admin views. It scales to zero and verifies each
  user's Firebase ID token. **Cloud Run Jobs** on **Cloud Scheduler** run discovery, harvesting, scoring, comment
  sampling and the FinOps report.
- **Firestore:** holds the live workflow state: script versions, compliance results, approvals, the audit trail,
  avatars, image selections, video plans and media approvals.
- **Firebase:** **Hosting** serves the Next.js app and routes `/api/**` to Cloud Run. **Auth** protects every page
  and API call.
- **BigQuery** holds the analytical corpus and **Cloud Storage** holds the private media.

## Demo video script (target 3:30, hard limit 4:00)

Record at 1920×1080 in the deployed app, signed in. Speak at an even pace: about 150 words per minute fits this
script.

| Time | Screen | Voice-over |
|---|---|---|
| 0:00–0:20 | Title card, then the **Overview** page | "Dubai has more than 33,000 registered brokers, and most of them sell on video. Which pitches actually work, and can AI produce a compliant one in minutes? This is PitchOps AI." |
| 0:20–0:45 | **Overview** tiles: brokers → channels → videos → deep-analysed | "We matched the official broker register to 1,141 YouTube channels and 227,000 videos. Gemini on Vertex AI watched the top videos straight from YouTube, with nothing downloaded, and tagged every relevant video from the last two years." |
| 0:45–1:15 | **Personas**: open the matrix, click one cell to show its evidence videos | "The result is a persona database: how brokers sell, who they sell to and in what format. Every link is rated on views, content quality and compliance risk, and it opens straight to its evidence videos. These are patterns, never profiles of individuals." |
| 1:15–1:35 | **Companies**: open a company, scroll the report, click Download Markdown | "Every company gets a report on its persona mix, funnel, strengths and gaps, with each point cited to a video." |
| 1:35–2:15 | **Script Studio**: open a script, run the compliance check, show a flag and its explanation, regenerate one line, then Approve | "Pick a property and a buyer persona, and Gemini writes a grounded script. The compliance check applies UAE advertising rules. Here it flags an unsourced yield claim, explains why, and rewrites only that line. A human approves, and the approval is frozen into the audit trail." |
| 2:15–2:45 | **Media**: open a plan, show the shot list, cost estimate and budget guard, then the avatars page | "Approved scripts become video plans: a shot list, a presenter from eight fictional avatars, and a cost estimate checked against a hard budget. Nothing is generated until the owner approves." |
| 2:45–3:15 | Play about 25 seconds of a finished video (Bayn 9:16, then a few seconds of Bugatti 16:9) | "Veo animates the presenter and the property, Cloud TTS narrates, and Lyria adds the music. This is a finished pitch in the urgency-closer style." |
| 3:15–3:35 | **FinOps** page | "Every Gemini, Veo and TTS call is logged against daily and total caps. The whole build, including sixteen videos, has used about a third of its two-hundred-dollar cap." |
| 3:35–3:50 | Closing card: URL and repo | "Firebase Hosting and Auth, Firestore, Cloud Run and Gemini: from public content to a compliant pitch, in minutes. PitchOps AI." |
