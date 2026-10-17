"""Investor walkthrough (target ≈ 8:00). Same pipeline as scenes.py: card = designed slide with slow zoom,
rec = live screen recording, clip = a finished PitchOps video. Select with DEMO_SCENES=investor."""

VOICE = "en-US-Chirp3-HD-Charon"

SCENES = [
    {"id": "i00_title", "kind": "card",
     "card": {"title": "PitchOps AI", "sub": "The AI sales-content engine for real estate",
              "lines": ["Learn what sells. Write it compliantly. Produce it in minutes."]},
     "text": "PitchOps AI. The AI sales-content engine for real estate."},

    {"id": "i01_problem", "kind": "card",
     "card": {"title": "The problem", "sub": "Real estate is sold on video, without evidence",
              "lines": ["33,565 registered brokers in Dubai, most of them selling on video",
                        "No one can see which pitch works, for which buyer",
                        "One wrong claim, such as a guaranteed return, is a regulatory risk",
                        "A single targeted video still takes days of agency, legal and editing work"]},
     "text": "Dubai alone has more than thirty-three thousand registered real-estate brokers, and almost all of "
             "them sell on video. Nobody can tell which pitch actually works, which buyer it reaches, or whether a line in it "
             "breaks advertising rules. One promise of a guaranteed return can become a regulatory problem. And "
             "producing a single targeted, compliant video still takes days of agency briefs, legal review and "
             "editing."},

    {"id": "i02_insight", "kind": "card",
     "card": {"title": "Our insight", "sub": "The market's own content is the dataset",
              "lines": ["Hundreds of thousands of public sales videos already exist",
                        "AI can now watch them, at scale, for cents",
                        "Turn them into evidence, then into the next compliant pitch"]},
     "text": "Our insight is simple. The answer is already public. The market has published hundreds of thousands "
             "of sales videos, and with today's multimodal AI we can watch them at scale, for cents each. If we "
             "turn that content into evidence about what works, we can use the same evidence to write and "
             "produce the next pitch, safely."},

    {"id": "i03_solution", "kind": "card",
     "card": {"title": "One governed workflow", "sub": "Learn  →  Write  →  Check  →  Produce",
              "lines": ["Learn: an evidence-rated persona playbook from the market's videos",
                        "Write: grounded scripts for a property and a buyer persona",
                        "Check: UAE advertising rules, explained, with a human approval",
                        "Produce: a finished presenter video, inside a hard budget"]},
     "text": "PitchOps AI is one governed workflow with four steps. Learn: build an evidence-rated playbook from "
             "the market's own videos. Write: generate grounded scripts for a specific property and buyer. "
             "Check: apply advertising rules, explain every risk, and require a human approval. Produce: turn "
             "the approved script into a finished presenter video, within a hard budget."},

    {"id": "i04_data", "kind": "rec", "action": "overview_long",
     "text": "Everything starts with data. We connect the official Dubai Land Department broker register to the "
             "public channels of those brokers and their companies. Today that is more than eleven hundred "
             "channels and two hundred and twenty-seven thousand videos. We keep the relevant, recent ones, "
             "nearly sixty-six thousand. Gemini tags every one of them, and watches the top-trending videos "
             "straight from YouTube, without downloading anything. It extracts the hook, the sales tactics, the "
             "target buyer, every claim made on screen, and the compliance risk, each with a timestamp. This evidence base grows every day, and it is the "
             "foundation competitors would have to rebuild."},

    {"id": "i05_personas", "kind": "rec", "action": "personas_long",
     "text": "From that evidence we build the persona playbook. Rows are how brokers sell: the luxury showcase, "
             "the market educator, the payment-plan closer. Columns are who they sell to: the high-net-worth "
             "investor, the relocating family, the yield seeker. Every cell is rated on views, momentum, content "
             "quality and compliance risk. And this is the important part: every rating opens straight to the "
             "evidence videos behind it, with the hooks, calls to action and buyer questions that drove it. These are aggregated "
             "patterns, never profiles of individual people."},

    {"id": "i05b_sellers", "kind": "rec", "action": "persona_tab_seller",
     "text": "Let's look at who is selling. The data surfaces clear seller personas. The most common is the "
             "Resort-Living Showcase Specialist, in more than twenty-three thousand videos. Then the Market "
             "Educator, the Elite Brand Prestige Showcase, and the Master Developer Showcase. Closers, like the "
             "Pre-Launch Urgency Closer and the Micro-Installment Closer, push for a decision, while the Milestone "
             "and Due Diligence Advisor lowers the buyer's risk. These are the selling styles our customers can "
             "choose to adopt, and the ones they should avoid."},

    {"id": "i05c_buyers", "kind": "rec", "action": "persona_tab_buyer",
     "text": "And this is who they are selling to. The largest buyer personas are families buying into a resort "
             "lifestyle, off-plan investors chasing yield and capital growth, cash-flow yield investors, and "
             "high-net-worth buyers seeking status and branded waterfront homes. There are first-time buyers, and "
             "international expats, some investing and some relocating. Every buyer persona carries a motive, "
             "invest, settle or both, and a trigger, such as yield, visa, family or status. That is what lets "
             "PitchOps match the right selling style to the right buyer."},

    {"id": "i05d_findings", "kind": "card",
     "card": {"title": "What the data shows", "sub": "Observations from the persona ratings",
              "lines": ["Most common is not most effective: Resort-Living Showcase, 23,504 videos, rated D",
                        "Elite Brand Prestige Showcase is rated A, the top seller style",
                        "Yield & Tax pitches carry the highest compliance risk: 20% of evidence flagged",
                        "Family Space Upgraders: 52% of comments show buying intent, only 1,770 videos"]},
     "text": "And the data already says things the market doesn't know. The most common style is not the most "
             "effective: the resort-living showcase is everywhere, but it is rated D, while the elite brand "
             "prestige showcase is rated A. Yield and tax pitches carry the highest compliance risk, with one in "
             "five of their videos flagged. And family upgraders are underserved: more than half of the comments "
             "on those videos show buying intent, yet fewer than two thousand videos target them. Every one of "
             "these findings is a campaign brief."},

    {"id": "i06_company", "kind": "rec", "action": "company_long",
     "text": "For a brokerage owner or a developer, the same engine becomes competitive intelligence. Every "
             "brokerage gets a report: its persona mix, its funnel from awareness to decision, its strengths, "
             "its gaps, and its opportunities. Each point is cited to a real video. A marketing director can see "
             "exactly where a competitor is winning, and where the open space is, in minutes rather than weeks."},

    {"id": "i07_properties", "kind": "rec", "action": "properties",
     "text": "The engine also tracks properties: which projects brokers talk about most, how those videos "
             "perform, and the verified facts that a pitch is allowed to cite."},

    {"id": "i08_studio", "kind": "rec", "action": "studio",
     "text": "Now we move from insight to action. In Script Studio, a marketer picks a property and a buyer "
             "persona, and Gemini writes a script grounded only in verified facts, using the tactics the playbook "
             "shows work for that buyer."},

    {"id": "i09_compliance", "kind": "rec", "action": "compliance",
     "text": "Compliance is built in, not bolted on. Here is a deliberately bad draft that promises guaranteed "
             "twelve percent returns. The rule engine blocks the guaranteed-return claim and the unsourced number. "
             "Gemini explains each risk and rewrites only the offending line. "
             "Approval stays locked until the script is clean. When a human approves, the decision is frozen "
             "into an audit trail. For a regulated industry, that governance is what turns AI from a risk into a "
             "tool a compliance officer can sign off."},

    {"id": "i10_media", "kind": "rec", "action": "media",
     "text": "Approved scripts become video plans. Each plan has a shot list, a presenter chosen from a cast of "
             "fictional, multilingual AI avatars, and a cost estimate checked against a hard budget. Nothing is "
             "generated, and nothing is spent, until the owner watches a free preview and approves."},

    {"id": "i11_plan", "kind": "rec", "action": "plan",
     "text": "Here is what comes out. Veo animates the presenter and the property, Google text-to-speech "
             "narrates, and Lyria composes the music. This is a one-minute luxury walkthrough."},
    {"id": "i12_clip16", "kind": "clip", "file": "plan_bugatti_residences_16x9_status_luxury.mp4", "ss": 0,
     "dur": 20, "text": ""},
    {"id": "i13_short_intro", "kind": "card",
     "card": {"title": "Same engine, different persona", "sub": "A 9:16 Short for the pre-launch urgency buyer",
              "lines": []},
     "text": "And the same engine, aimed at a different buyer persona, produces a vertical short for social."},
    {"id": "i14_clip9", "kind": "clip", "file": "plan_bayn_9x16_fomo_scarcity.mp4", "ss": 0, "dur": 16,
     "text": ""},

    {"id": "i15_finops", "kind": "rec", "action": "finops",
     "text": "Every AI call is metered and capped, so the economics are visible from day one. Analysing a video "
             "costs about two cents. A grounded, checked script costs less than one cent. A finished presenter "
             "video costs two to four dollars in AI, a small fraction of a traditional shoot. "
             "That cost curve is what makes personalised video at scale possible."},

    {"id": "i16_model", "kind": "card",
     "card": {"title": "Business model", "sub": "SaaS seats + usage-based production",
              "lines": ["Brokerage seats: playbook, competitor reports, Script Studio",
                        "Production credits: per finished, approved video",
                        "Enterprise: developers and portals, with brand kits and approval roles",
                        "Market intelligence reports for developers launching projects"]},
     "text": "Our planned business model has two engines. First, software seats for brokerages: the playbook, "
             "competitor reports and Script Studio. Second, usage-based production credits for every finished, "
             "approved video, priced well above our AI cost and far below an agency. On top, enterprise plans "
             "for developers and property portals."},

    {"id": "i17_gtm", "kind": "card",
     "card": {"title": "Go-to-market", "sub": "Start where the data and the pain are densest",
              "lines": ["Phase 1: Dubai brokerages (9,862 registered companies) and developers",
                        "Phase 2: property portals and developer marketing teams",
                        "Phase 3: other regulated markets: Abu Dhabi, Saudi Arabia, India, UK"]},
     "text": "We start where the data and the pain are densest: Dubai, with nearly ten thousand registered "
             "brokerage companies and a steady stream of developer launches. Next come property portals and "
             "developer marketing teams, who need content at volume. Then we expand to other regulated property "
             "markets, such as Abu Dhabi, Saudi Arabia, India and the UK, by adding a rule pack for each "
             "regulator rather than rebuilding the product."},

    {"id": "i18_moat", "kind": "card",
     "card": {"title": "Why we win", "sub": "Evidence  ·  Compliance  ·  Governance",
              "lines": ["A growing evidence graph of what sells, built from the market's own content",
                        "Regulator-specific rule packs with explainable flags",
                        "Human approval, audit trail and cost caps in every step",
                        "Built on Google's Gemini, Veo and Lyria, riding a falling cost curve"]},
     "text": "Why do we win? Three reasons. First, evidence: a growing graph of what actually sells, built from "
             "the market's own content, which generic AI writers do not have. Second, compliance: rule packs per "
             "regulator, with explanations a compliance officer can trust. Third, governance: human approval, an "
             "audit trail and cost caps at every step."},

    {"id": "i19_roadmap", "kind": "card",
     "card": {"title": "Roadmap", "sub": "From insight tool to the content operating system for real estate",
              "lines": ["Arabic, Russian, Hindi and Chinese scripts and voices",
                        "Instagram Reels and TikTok, publishing from the app",
                        "Closed loop: real performance feeds back into the playbook",
                        "Multi-tenant teams with marketer, compliance and approver roles"]},
     "text": "On the roadmap: scripts and voices in Arabic, Russian, Hindi and Chinese, matching the buyers who "
             "drive this market. Reels and TikTok, with publishing straight from the app. A closed loop, where "
             "the real performance of every published video flows back into the playbook, so recommendations "
             "get sharper with every campaign. And multi-tenant teams, with separate marketer, compliance and "
             "approver roles."},

    {"id": "i19b_copilot", "kind": "card",
     "card": {"title": "The future: a live sales co-pilot", "sub": "From the right video to the right response, on every call",
              "lines": ["Listens to calls and chats, with the customer's consent",
                        "Recognises the buyer persona from what the customer says",
                        "Puts the next best line on the agent's screen, grounded in verified facts",
                        "Warns before a non-compliant promise is made",
                        "Logs objections and outcomes back into the playbook and the CRM"]},
     "text": "The biggest opportunity is live. Most property deals still close on the phone and in chat, so we "
             "are extending PitchOps into a real-time co-pilot for call centres and sales teams. With the "
             "customer's consent, it listens to the conversation and recognises the buyer persona from what the "
             "customer says. It then puts the next best line on the agent's screen, grounded in verified property "
             "facts and in the style the playbook shows works for that buyer. If the agent is about to promise "
             "something non-compliant, such as a guaranteed return, it warns them first. After the call, it logs "
             "objections and outcomes to the CRM, and those outcomes flow back into the playbook."},

    {"id": "i19c_copilot_example", "kind": "card",
     "card": {"title": "On a live call", "sub": "Caller: \"Is the eight percent return guaranteed?\"",
              "lines": ["Persona detected: Cash Flow Yield Investor",
                        "Suggested answer: no guarantee; the verified facts and payment plan instead",
                        "Compliance: the guaranteed-return phrasing is blocked on screen",
                        "After the call: the objection is logged for the next campaign"]},
     "text": "Here is how that looks. A caller asks whether an eight percent return is guaranteed. PitchOps "
             "recognises a cash-flow yield investor. It suggests a compliant answer: no guarantee, and instead "
             "the verified facts and the payment plan. It blocks the risky phrasing on screen, and records the "
             "objection, so the next video campaign answers it before the customer even asks. The same engine "
             "can power WhatsApp and web chat, so every customer conversation, not just every video, gets the "
             "right response."},

    {"id": "i20_close", "kind": "card",
     "card": {"title": "PitchOps AI", "sub": "Learn what sells. Write it compliantly. Produce it in minutes.",
              "lines": ["Kunal Mishra  ·  Manjeet Malwan", "pitchops-ai-2026.web.app",
                        "github.com/drkunalmishra/pitchops-ai"]},
     "text": "PitchOps AI turns the market's own content into evidence, and evidence into compliant pitches, in "
             "minutes. We are Kunal Mishra and Manjeet Malwan, and we are looking for investors and launch "
             "partners who want to build the content operating system for real estate. Thank you."},
]
