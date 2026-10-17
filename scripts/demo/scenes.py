"""Demo video plan (target ≈ 3:45, hard limit 4:00). Each scene = narration + what the screen does while it plays.
kind: card (generated title/end card), rec (live screen recording), clip (cut to a finished PitchOps video)."""

import os
from pathlib import Path

# outputs (Chrome login profile, audio, frames, renders) live OUTSIDE the repo
DATA = Path(os.environ.get("DEMO_DATA", "/private/tmp/claude-501/-Users-mamtamishra-Desktop-Project-BigSell-PitchOPsAI/0ed26401-5975-47aa-8f54-6b0a9df801f4/scratchpad/demo"))
SITE = "https://pitchops-ai-2026.web.app"
VOICE = "en-US-Chirp3-HD-Charon"

SCENES = [
    {"id": "s00_title", "kind": "card",
     "text": "PitchOps AI, by team SellItR8."},
    {"id": "s01_hook", "kind": "rec", "action": "overview_top",
     "text": "Dubai has more than thirty-three thousand registered real-estate brokers, and most of them sell on "
             "video. But nobody knows which pitches actually work, who they reach, or whether they are compliant. "
             "PitchOps AI answers that, and then writes and produces the compliant pitch for you."},
    {"id": "s02_funnel", "kind": "rec", "action": "overview_funnel",
     "text": "We started from the Dubai Land Department broker register, matched it to eleven hundred YouTube "
             "channels, and harvested two hundred and twenty-seven thousand videos through the YouTube Data API. "
             "Gemini on Vertex AI tagged every relevant video from the last two years, and watched the top-trending "
             "ones straight from their YouTube links. Nothing is downloaded."},
    {"id": "s03_personas", "kind": "rec", "action": "personas",
     "text": "The result is a persona database. Rows are how brokers sell; columns are who they sell to. Every cell "
             "is rated on views, trending, content quality and compliance risk, and one click opens the evidence "
             "videos behind it. These are aggregated patterns, never profiles of individual brokers."},
    {"id": "s04_company", "kind": "rec", "action": "company",
     "text": "For every brokerage on the shortlist, Gemini writes a cited report: persona mix, funnel, strengths, "
             "gaps and opportunities. Each point links back to a real video, and the report downloads as Markdown."},
    {"id": "s04b_properties", "kind": "rec", "action": "properties",
     "text": "Properties are ranked by how often brokers discuss them and how those videos perform, and each one "
             "carries grounded facts that the scripts are allowed to cite."},
    {"id": "s05_studio", "kind": "rec", "action": "studio",
     "text": "Now the pitch. Script Studio holds a hundred and eleven Gemini-written scripts, each grounded in "
             "verified property facts and aimed at one buyer persona."},
    {"id": "s06_compliance", "kind": "rec", "action": "compliance",
     "text": "Here is a deliberately bad draft that promises guaranteed twelve percent returns. The compliance "
             "engine applies UAE advertising rules. It blocks the guaranteed-return claim and the unsourced number, "
             "explains each flag, and suggests a fix. Gemini can rewrite just the offending line, and approval stays "
             "locked until the script is clean. Every approval is frozen into an audit trail in Firestore."},
    {"id": "s07_media", "kind": "rec", "action": "media",
     "text": "Approved scripts become video plans: a shot list, one of eight fictional presenter avatars, and a Veo "
             "cost estimate checked against a hard media budget. Nothing is generated until the owner watches a "
             "free preview and approves."},
    {"id": "s08_plan", "kind": "rec", "action": "plan",
     "text": "Here is the finished pitch for Bugatti Residences. Veo animates the presenter and the property, "
             "Cloud Text-to-Speech narrates, and Lyria composes the music."},
    {"id": "s09_clip", "kind": "clip", "file": "plan_bugatti_residences_16x9_status_luxury.mp4", "ss": 0, "dur": 22,
     "text": ""},
    {"id": "s10_finops", "kind": "rec", "action": "finops",
     "text": "Every Gemini, Veo and speech call is logged and capped. The whole build, analysing two hundred and "
             "twenty-seven thousand videos and producing sixteen finished videos, used about sixty-nine dollars of "
             "free-trial credit."},
    {"id": "s11_close", "kind": "card",
     "text": "PitchOps AI runs on Firebase Hosting and Auth, Firestore, Cloud Run, and Gemini on Vertex AI. From "
             "public content to a compliant pitch, in minutes. Thank you."},
]
