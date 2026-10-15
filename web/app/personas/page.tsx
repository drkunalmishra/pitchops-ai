"use client";

import { useMemo, useState } from "react";
import { Band, Card, Page, Pill, Status, VideoCard, fmt, human, useApi, type Video } from "@/components/ui";

type Persona = {
  persona_id: string;
  layer: "seller" | "buyer" | "format";
  name: string;
  description: string | null;
  motive: string | null;
  member_count: number;
  deep_videos: number;
  channel_count: number;
  company_count: number;
  rating_band: string | null;
  confidence: number | null;
  trending_median: number | null;
  opi_median: number | null;
  sales_pressure_median: number | null;
  compliance_risk_rate: number | null;
  attributes: { top_triggers?: Record<string, number>; top_origins?: Record<string, number> } | null;
  works_with: string[];
  avoid: string[];
};
type Cell = { seller: string; buyer: string; videos: number; deep_videos: number; trending: number | null; sales_pressure: number | null };
type Matrix = { sellers: string[]; buyers: string[]; cells: Cell[] };
type CellDetail = { videos: Video[]; hooks: string[]; ctas: string[]; questions: string[]; objections: string[] };

const TABS = [
  ["seller", "Seller personas"],
  ["buyer", "Buyer personas"],
  ["format", "Formats"],
] as const;

const top = (o?: Record<string, number>) =>
  Object.entries(o || {})
    .sort((a, b) => b[1] - a[1])
    .slice(0, 3)
    .map(([k]) => human(k));

function PersonaCard({ p }: { p: Persona }) {
  return (
    <article className="rounded-xl border border-navy-700 bg-navy-900 p-4">
      <div className="flex items-start justify-between gap-2">
        <h3 className="font-medium text-white">{p.name}</h3>
        <Band band={p.rating_band} confidence={p.confidence} />
      </div>
      {p.description && <p className="mt-1 text-sm text-slate-300">{p.description}</p>}
      <dl className="mt-3 grid grid-cols-3 gap-2 text-xs">
        <div>
          <dt className="text-slate-400">Videos</dt>
          <dd className="tabular-nums text-white">{fmt(p.member_count)}</dd>
        </div>
        <div>
          <dt className="text-slate-400">Deep</dt>
          <dd className="tabular-nums text-white">{fmt(p.deep_videos)}</dd>
        </div>
        <div>
          <dt className="text-slate-400">Companies</dt>
          <dd className="tabular-nums text-white">{fmt(p.company_count)}</dd>
        </div>
        <div>
          <dt className="text-slate-400">Trending (median)</dt>
          <dd className="tabular-nums text-white">{fmt(p.trending_median, 2)}</dd>
        </div>
        <div>
          <dt className="text-slate-400">Sales pressure</dt>
          <dd className="tabular-nums text-white">{fmt(p.sales_pressure_median, 1)}</dd>
        </div>
        <div>
          <dt className="text-slate-400">Risky claims</dt>
          <dd className="tabular-nums text-white">
            {p.compliance_risk_rate === null ? "—" : `${fmt(100 * p.compliance_risk_rate)}%`}
          </dd>
        </div>
      </dl>
      {top(p.attributes?.top_triggers).length > 0 && (
        <div className="mt-3 flex flex-wrap gap-1">
          {top(p.attributes?.top_triggers).map((x) => (
            <Pill key={x}>{x}</Pill>
          ))}
        </div>
      )}
      {p.works_with.length > 0 && (
        <div className="mt-3 text-xs">
          <div className="font-semibold text-teal-400">What works</div>
          <ul className="mt-1 list-disc pl-4 text-slate-300">
            {p.works_with.map((w) => (
              <li key={w}>{w}</li>
            ))}
          </ul>
        </div>
      )}
      {p.avoid.length > 0 && (
        <div className="mt-2 text-xs">
          <div className="font-semibold text-amber-300">Watch out</div>
          <ul className="mt-1 list-disc pl-4 text-slate-300">
            {p.avoid.map((w) => (
              <li key={w}>{w}</li>
            ))}
          </ul>
        </div>
      )}
    </article>
  );
}

function MatrixView({ m, onPick, picked }: { m: Matrix; onPick: (s: string, b: string) => void; picked: string | null }) {
  const [metric, setMetric] = useState<"videos" | "trending">("videos");
  const byKey = useMemo(() => new Map(m.cells.map((c) => [`${c.seller}|${c.buyer}`, c])), [m]);
  const vals = m.cells.filter((c) => m.buyers.includes(c.buyer)).map((c) => (metric === "videos" ? c.videos : c.trending ?? 0));
  const max = Math.max(1e-9, ...vals);
  return (
    <Card title="Persona matrix — seller × buyer">
      <div className="mb-3 flex flex-wrap items-center gap-2 text-sm" role="radiogroup" aria-label="Cell value">
        {(["videos", "trending"] as const).map((k) => (
          <button
            key={k}
            role="radio"
            aria-checked={metric === k}
            onClick={() => setMetric(k)}
            className={`rounded-lg px-3 py-1 ${metric === k ? "bg-teal-600 text-white" : "border border-navy-700 text-slate-300"}`}
          >
            {k === "videos" ? "Video count" : "Median trending"}
          </button>
        ))}
        <span className="text-xs text-slate-400">Darker = higher. Click a cell for evidence videos.</span>
      </div>
      <div className="overflow-x-auto">
        <table className="border-separate border-spacing-0.5 text-xs">
          <thead>
            <tr>
              <th className="sticky left-0 bg-navy-900 p-1 text-left font-medium text-slate-400">Seller \ Buyer</th>
              {m.buyers.map((b) => (
                <th key={b} scope="col" className="h-28 min-w-12 align-bottom font-normal text-slate-300">
                  <div className="mx-auto w-4 rotate-180 whitespace-nowrap [writing-mode:vertical-rl]">{human(b)}</div>
                </th>
              ))}
            </tr>
          </thead>
          <tbody>
            {m.sellers.map((s) => (
              <tr key={s}>
                <th scope="row" className="sticky left-0 whitespace-nowrap bg-navy-900 p-1 pr-3 text-left font-normal text-slate-300">
                  {human(s)}
                </th>
                {m.buyers.map((b) => {
                  const c = byKey.get(`${s}|${b}`);
                  const v = c ? (metric === "videos" ? c.videos : c.trending ?? 0) : 0;
                  const a = c ? 0.12 + 0.88 * (v / max) : 0;
                  const key = `${s}|${b}`;
                  return (
                    <td key={b} className="p-0">
                      <button
                        disabled={!c}
                        onClick={() => onPick(s, b)}
                        title={c ? `${human(s)} × ${human(b)}: ${fmt(c.videos)} videos, ${fmt(c.deep_videos)} deep, trending ${fmt(c.trending, 2)}` : "no videos"}
                        aria-label={`${human(s)} by ${human(b)}`}
                        className={`h-9 w-12 rounded text-[11px] tabular-nums ${picked === key ? "ring-2 ring-white" : ""} ${a > 0.55 ? "text-navy-950" : "text-slate-200"}`}
                        style={{ background: c ? `rgba(45, 212, 191, ${a})` : "transparent" }}
                      >
                        {c ? (metric === "videos" ? (c.videos >= 1000 ? `${Math.round(c.videos / 100) / 10}k` : c.videos) : fmt(c.trending, 1)) : ""}
                      </button>
                    </td>
                  );
                })}
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </Card>
  );
}

function CellPanel({ seller, buyer }: { seller: string; buyer: string }) {
  const { data, error } = useApi<CellDetail>(`/v1/explore/matrix/cell?seller=${encodeURIComponent(seller)}&buyer=${encodeURIComponent(buyer)}`);
  return (
    <Card title={`${human(seller)} × ${human(buyer)} — evidence`}>
      <Status error={error} loading={!data} />
      {data && (
        <div className="grid gap-4 lg:grid-cols-3">
          <div className="space-y-2 lg:col-span-2">
            {data.videos.length === 0 && <p className="text-sm text-slate-400">No evidence videos.</p>}
            {data.videos.map((v) => (
              <VideoCard key={v.video_id} v={v} />
            ))}
          </div>
          <div className="space-y-4 text-sm">
            {[
              ["Typical hooks", data.hooks],
              ["Typical CTAs", data.ctas],
              ["Audience questions", data.questions],
              ["Objections", data.objections],
            ].map(([t, xs]) => (
              <div key={t as string}>
                <div className="text-xs font-semibold uppercase tracking-wider text-slate-400">{t as string}</div>
                {(xs as string[]).length ? (
                  <div className="mt-1 flex flex-wrap gap-1">
                    {(xs as string[]).map((x) => (
                      <Pill key={x}>{human(x)}</Pill>
                    ))}
                  </div>
                ) : (
                  <p className="mt-1 text-xs text-slate-400">
                    {(t as string).startsWith("Audience") || t === "Objections" ? "Comment classification pending" : "—"}
                  </p>
                )}
              </div>
            ))}
          </div>
        </div>
      )}
    </Card>
  );
}

export default function PersonasPage() {
  const { data: ps, error } = useApi<Persona[]>("/v1/explore/personas");
  const { data: m } = useApi<Matrix>("/v1/explore/matrix");
  const [tab, setTab] = useState<(typeof TABS)[number][0]>("seller");
  const [pick, setPick] = useState<[string, string] | null>(null);
  const list = (ps || []).filter((p) => p.layer === tab && !p.persona_id.startsWith("buyer:agent_industry"));
  return (
    <Page
      title="Persona Explorer"
      sub="Patterns, not people: seller tactics × buyer personas × formats, aggregated from per-video labels and rated on OPI and trending."
    >
      <Status error={error} loading={!ps} />
      {m && (
        <div className="space-y-6">
          <MatrixView m={m} onPick={(s, b) => setPick([s, b])} picked={pick ? `${pick[0]}|${pick[1]}` : null} />
          {pick && <CellPanel key={pick.join("|")} seller={pick[0]} buyer={pick[1]} />}
        </div>
      )}
      {ps && (
        <div className="mt-8">
          <div role="tablist" aria-label="Persona layer" className="mb-4 flex gap-1">
            {TABS.map(([k, label]) => (
              <button
                key={k}
                role="tab"
                aria-selected={tab === k}
                onClick={() => setTab(k)}
                className={`rounded-lg px-3 py-1.5 text-sm ${tab === k ? "bg-navy-800 text-white" : "text-slate-300 hover:text-white"}`}
              >
                {label} ({ps.filter((p) => p.layer === k).length})
              </button>
            ))}
          </div>
          <div role="tabpanel" className="grid gap-4 sm:grid-cols-2 xl:grid-cols-3">
            {list.map((p) => (
              <PersonaCard key={p.persona_id} p={p} />
            ))}
          </div>
          <p className="mt-4 text-xs text-slate-400">
            Band A–E = percentile of 0.5·OPI median + 0.5·trending median; faded when confidence &lt; 0.4. Names are
            code-generated until Gemini naming runs.
          </p>
        </div>
      )}
    </Page>
  );
}
