"use client";

import Link from "next/link";
import { Card, Page, Pill, Status, Tile, compact, fmt, human, mmss, useApi, useParam, yt } from "@/components/ui";

type Seg = { start_sec: number; end_sec: number; segment_type: string; mode: string; summary: string; on_screen_text: string | null };
type Claim = {
  ts_sec: number;
  quote: string;
  claim_type: string;
  has_source: boolean;
  source_text: string | null;
  source_check?: string;
  source_reported?: string;
  origin?: string;
  is_risky: boolean;
  risk_note: string | null;
};
type Mention = { ts_sec: number; project_name: string | null; developer: string | null; area: string | null; emirate: string | null; property_type: string | null; price_text: string | null };
type V = {
  video_id: string;
  title: string;
  duration_sec: number;
  is_short: boolean;
  published_at: string;
  is_relevant: boolean;
  relevance_reason: string | null;
  relevance_source: string | null;
  channel: string;
  company_id: string | null;
  company: string | null;
  views: number | null;
  trending: number | null;
  eng_rate: number | null;
  opi: number | null;
  status: string | null;
  model_id: string | null;
  coverage: string | null;
  clips: { start: number; end: number }[] | null;
  overview: Record<string, any> | null;
  segments: Seg[] | null;
  claims: Claim[] | null;
  property_mentions: Mention[] | null;
  sales_pressure_score: number | null;
  evidence_density: number | null;
  education_to_sales: number | null;
  pitch_share: number | null;
  verification_status: string | null;
  audience_status: string | null;
  comments_collected: number | null;
  top_questions: any;
  objection_topics: any;
};

const MODE: Record<string, string> = { education: "bg-teal-500", pitch: "bg-amber-400", neutral: "bg-slate-500" };

function Timeline({ segs, dur }: { segs: Seg[]; dur: number }) {
  return (
    <div>
      <div className="flex h-5 w-full gap-0.5 overflow-hidden rounded" aria-hidden>
        {segs.map((s, i) => (
          <div
            key={i}
            className={`${MODE[s.mode] || MODE.neutral} h-5`}
            style={{ width: `${(100 * Math.max(0.5, s.end_sec - s.start_sec)) / Math.max(dur, 1)}%` }}
            title={`${mmss(s.start_sec)}–${mmss(s.end_sec)} ${human(s.segment_type)} (${s.mode})`}
          />
        ))}
      </div>
      <div className="mt-2 flex gap-4 text-xs text-slate-300">
        {Object.entries(MODE).map(([k, c]) => (
          <span key={k} className="flex items-center gap-1">
            <span className={`inline-block h-2.5 w-2.5 rounded-sm ${c}`} /> {human(k)}
          </span>
        ))}
      </div>
    </div>
  );
}

export default function VideoPage() {
  const id = useParam("id");
  const { data: v, error } = useApi<V>(id ? `/v1/explore/videos/${encodeURIComponent(id)}` : null);
  const ov = v?.overview;
  const analysed = v?.clips?.reduce((a, c) => Math.max(a, c.end), 0) || v?.duration_sec || 0;
  return (
    <Page title={v?.title || "Video"} sub={v && <>{v.channel}{v.company_id && <> · <Link className="hover:text-teal-400" href={`/company/?id=${v.company_id}`}>{v.company}</Link></>}</>}>
      <Status error={error} loading={!v} />
      {v && (
        <div className="space-y-6">
          {!v.is_relevant && (
            <p className="rounded-lg border border-amber-700 bg-amber-950/40 p-3 text-sm text-amber-200">
              Flagged not relevant ({v.relevance_source}): {v.relevance_reason}. Excluded from all analysis.
            </p>
          )}
          <div className="grid gap-6 lg:grid-cols-3">
            <div className="lg:col-span-2">
              <div className="aspect-video overflow-hidden rounded-xl border border-navy-700">
                <iframe
                  className="h-full w-full"
                  src={`https://www.youtube-nocookie.com/embed/${v.video_id}`}
                  title={v.title}
                  allow="encrypted-media; picture-in-picture"
                  allowFullScreen
                />
              </div>
            </div>
            <div className="grid grid-cols-2 content-start gap-3">
              <Tile label="Views" value={compact(v.views)} />
              <Tile label="Trending" value={fmt(v.trending, 2)} />
              <Tile label="OPI" value={fmt(v.opi, 2)} />
              <Tile label="Length" value={mmss(v.duration_sec)} sub={v.is_short ? "Short" : "long-form"} />
              <Tile label="Sales pressure" value={fmt(v.sales_pressure_score, 1)} sub="/10, computed in code" />
              <Tile label="Evidence" value={fmt(v.evidence_density, 2)} sub="sourced claims / min" />
              <Tile label="Verification" value={<span className="text-base">{human(v.verification_status) || "—"}</span>} />
              <Tile label="Pitch share" value={v.pitch_share === null ? "—" : `${fmt(100 * v.pitch_share)}%`} />
            </div>
          </div>
          {!ov && <Card><p className="text-sm text-slate-300">Not deep-analysed (outside the top-10-trending selection, or pending).</p></Card>}
          {ov && (
            <>
              <Card title="Overview">
                <p className="text-sm text-slate-200">{ov.summary}</p>
                <div className="mt-3 flex flex-wrap gap-1">
                  {[ov.archetype, ov.hook_type, ...(ov.sales_frameworks || []), ...(ov.buyer_personas || []), ov.buyer_motive, ...(ov.buyer_triggers || [])]
                    .filter(Boolean)
                    .map((x: string, i: number) => (
                      <Pill key={i}>{human(x)}</Pill>
                    ))}
                </div>
                <dl className="mt-3 grid gap-2 text-sm sm:grid-cols-2">
                  <div>
                    <dt className="text-xs text-slate-400">Hook (ends {mmss(ov.hook_end_sec)})</dt>
                    <dd className="text-slate-200">“{ov.hook_text}”</dd>
                  </div>
                  <div>
                    <dt className="text-xs text-slate-400">CTA ({human(ov.cta_type)})</dt>
                    <dd className="text-slate-200">{ov.cta_text || "—"}</dd>
                  </div>
                </dl>
                <p className="mt-3 text-xs text-slate-400">
                  Analysed by {v.model_id} · coverage {v.coverage}
                  {v.coverage === "partial" && ` (${(v.clips || []).map((c) => `${mmss(c.start)}–${mmss(c.end)}`).join(", ")})`}
                </p>
              </Card>
              <Card title="Segments">
                <Timeline segs={v.segments || []} dur={analysed} />
                <table className="mt-4 w-full text-left text-sm">
                  <thead className="text-xs uppercase tracking-wider text-slate-400">
                    <tr>
                      <th className="py-1 pr-3">Time</th>
                      <th className="pr-3">Type</th>
                      <th className="pr-3">Mode</th>
                      <th>Summary / on-screen text</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-navy-800">
                    {(v.segments || []).map((s, i) => (
                      <tr key={i}>
                        <td className="py-1.5 pr-3 tabular-nums">
                          <a className="text-teal-400 hover:underline" href={yt(v.video_id, s.start_sec)} target="_blank" rel="noreferrer">
                            {mmss(s.start_sec)}–{mmss(s.end_sec)}
                          </a>
                        </td>
                        <td className="pr-3 text-slate-300">{human(s.segment_type)}</td>
                        <td className="pr-3 text-slate-300">{s.mode}</td>
                        <td className="text-slate-200">
                          {s.summary}
                          {s.on_screen_text && <div className="text-xs text-slate-400">“{s.on_screen_text}”</div>}
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </Card>
              <div className="grid gap-6 lg:grid-cols-2">
                <Card title={`Claims (${(v.claims || []).length})`}>
                  <ul className="space-y-3 text-sm">
                    {(v.claims || []).map((c, i) => (
                      <li key={i}>
                        <a className="tabular-nums text-teal-400 hover:underline" href={yt(v.video_id, c.ts_sec)} target="_blank" rel="noreferrer">
                          {mmss(c.ts_sec)}
                        </a>{" "}
                        <span className="text-slate-200">“{c.quote}”</span>
                        <div className="mt-0.5 flex flex-wrap gap-1 text-xs">
                          <Pill>{human(c.claim_type)}</Pill>
                          {c.is_risky && <span className="rounded-full bg-red-900/60 px-2 py-0.5 text-red-200">risky: {c.risk_note}</span>}
                          {c.has_source ? (
                            <span className="rounded-full bg-teal-900/60 px-2 py-0.5 text-teal-200">source shown: {c.source_text}</span>
                          ) : c.source_check === "self_cited" ? (
                            <span className="rounded-full bg-navy-800 px-2 py-0.5 text-slate-300">source not shown (claimed: {c.source_reported})</span>
                          ) : (
                            <span className="rounded-full bg-navy-800 px-2 py-0.5 text-slate-400">no source</span>
                          )}
                          {c.origin === "recheck" && <span className="rounded-full bg-navy-800 px-2 py-0.5 text-slate-400">added by re-check</span>}
                        </div>
                      </li>
                    ))}
                    {!(v.claims || []).length && <li className="text-slate-400">No claims.</li>}
                  </ul>
                </Card>
                <Card title="Property mentions">
                  <ul className="space-y-2 text-sm">
                    {(v.property_mentions || []).map((m, i) => (
                      <li key={i} className="text-slate-200">
                        <span className="tabular-nums text-teal-400">{mmss(m.ts_sec)}</span>{" "}
                        {[m.project_name, m.developer, m.area, m.emirate].filter(Boolean).join(" · ") || "—"}
                        {m.price_text && <span className="text-slate-400"> · {m.price_text}</span>}
                      </li>
                    ))}
                  </ul>
                </Card>
              </div>
            </>
          )}
          <Card title="Audience (comments)">
            {v.audience_status === "complete" ? (
              <p className="text-sm text-slate-300">
                {fmt(v.comments_collected)} comments collected (authors hashed, PII redacted). Intent and objection
                classification runs once Gemini access is restored.
              </p>
            ) : (
              <p className="text-sm text-slate-400">Comments unavailable for this video.</p>
            )}
          </Card>
        </div>
      )}
    </Page>
  );
}
