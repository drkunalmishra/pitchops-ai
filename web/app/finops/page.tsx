"use client";

import { Bars, Card, Page, Status, Tile, fmt, human, usd, useApi } from "@/components/ui";

type FinOps = {
  as_of: string;
  total_usd: number;
  today_usd: number;
  by_phase: Record<string, number>;
  by_provider: Record<string, number>;
  by_day: Record<string, Record<string, number>>;
  quota_by_day: Record<string, number>;
  quota_cap: number;
  phase_caps: Record<string, number>;
  project_cap_usd: number;
  project_cap_pct: number;
  trial_credit_usd: number;
  projection_remaining: Record<string, number>;
  projected_total_usd: number;
  unit_costs: Record<string, number | null>;
  note: string;
  bigquery_scope?: string;
};

const sum = (o: Record<string, number>) => Object.values(o).reduce((a, b) => a + b, 0);

export default function FinOpsPage() {
  const { data: f, error } = useApi<FinOps>("/v1/finops");
  const phases = f ? Array.from(new Set([...Object.keys(f.phase_caps || {}), ...Object.keys(f.by_phase)])).filter((p) => /^P\d$/.test(p)).sort() : [];
  return (
    <Page title="FinOps" sub="Every cost is an estimate at list price, before free tiers and trial credits. Real spend lives in Cloud Billing → Reports.">
      <Status error={error} loading={!f} />
      {f && (
        <div className="space-y-6">
          <div className="grid grid-cols-2 gap-4 md:grid-cols-5">
            <Tile label="Spend to date" value={usd(f.total_usd)} sub={`${fmt(f.project_cap_pct, 1)}% of ${usd(f.project_cap_usd, 0)} cap`} />
            <Tile label="Today" value={usd(f.today_usd)} />
            <Tile label="Projected total" value={usd(f.projected_total_usd, 0)} sub="incl. remaining phases" />
            <Tile label="Headroom to cap" value={usd(f.project_cap_usd - f.projected_total_usd, 0)} sub={`trial credit ${usd(f.trial_credit_usd, 0)}`} />
            <Tile label="Report as of" value={<span className="text-base">{new Date(f.as_of).toLocaleString()}</span>} />
          </div>

          <Card title="Cumulative vs caps">
            <div className="relative h-6 rounded bg-navy-800" role="img" aria-label={`Spent ${usd(f.total_usd)}, projected ${usd(f.projected_total_usd, 0)}, cap ${usd(f.project_cap_usd, 0)}, trial ${usd(f.trial_credit_usd, 0)}`}>
              <div className="absolute inset-y-0 left-0 rounded bg-teal-900" style={{ width: `${(100 * f.projected_total_usd) / f.trial_credit_usd}%` }} />
              <div className="absolute inset-y-0 left-0 rounded bg-teal-400" style={{ width: `${Math.max(0.5, (100 * f.total_usd) / f.trial_credit_usd)}%` }} />
              <div className="absolute inset-y-[-4px] w-0.5 bg-white" style={{ left: `${(100 * f.project_cap_usd) / f.trial_credit_usd}%` }} />
            </div>
            <div className="mt-2 flex flex-wrap gap-4 text-xs text-slate-300">
              <span><span className="mr-1 inline-block h-2.5 w-2.5 rounded-sm bg-teal-400" />Spent {usd(f.total_usd)}</span>
              <span><span className="mr-1 inline-block h-2.5 w-2.5 rounded-sm bg-teal-900" />Projected {usd(f.projected_total_usd, 0)}</span>
              <span><span className="mr-1 inline-block h-2.5 w-0.5 bg-white" />Project cap {usd(f.project_cap_usd, 0)}</span>
              <span>Full bar = {usd(f.trial_credit_usd, 0)} trial credit</span>
            </div>
          </Card>

          <div className="grid gap-6 lg:grid-cols-2">
            <Card title="Spend by phase vs phase cap (tick = cap)">
              <ul className="space-y-3">
                {phases.map((p) => {
                  const spent = f.by_phase[p] || 0;
                  const cap = f.phase_caps[p];
                  const proj = f.projection_remaining[p];
                  const scale = Math.max(cap || 0, spent, 1e-9);
                  return (
                    <li key={p} className="text-sm">
                      <div className="flex justify-between gap-3">
                        <span className="text-slate-300">{p}</span>
                        <span className="tabular-nums text-white">
                          {usd(spent)} <span className="text-slate-400">/ {usd(cap, 0)}{proj ? ` · projected +${usd(proj, 0)}` : ""}</span>
                        </span>
                      </div>
                      <div className="relative mt-1 h-2 rounded bg-navy-800">
                        <div className="h-2 rounded bg-teal-500" style={{ width: `${Math.max(0.5, (100 * spent) / scale)}%` }} />
                        {cap !== undefined && <div className="absolute inset-y-[-3px] right-0 w-0.5 bg-slate-300" />}
                      </div>
                    </li>
                  );
                })}
              </ul>
            </Card>
            <Card title="Spend by provider">
              <Bars
                rows={Object.entries(f.by_provider).map(([k, n]) => ({ k: human(k), n }))}
                format={(n) => usd(n)}
              />
              <p className="mt-3 text-xs text-slate-400">
                Veo, Imagen and Text-to-Speech appear here once media rendering (P7) starts. YouTube Data API is free
                within quota.
              </p>
            </Card>
            <Card title="Spend by day (IST)">
              <Bars rows={Object.entries(f.by_day).map(([k, v]) => ({ k, n: sum(v) }))} format={(n) => usd(n)} />
            </Card>
            <Card title={`YouTube quota units per day (cap ${fmt(f.quota_cap)}, Pacific day)`}>
              <Bars rows={Object.entries(f.quota_by_day).map(([k, n]) => ({ k, n }))} cap={f.quota_cap} />
            </Card>
          </div>

          <Card title="Unit costs">
            <table className="w-full text-left text-sm">
              <tbody className="divide-y divide-navy-800">
                <tr>
                  <td className="py-2 text-slate-300">Per deep-analysed video (Vertex)</td>
                  <td className="text-right tabular-nums">{usd(f.unit_costs.per_deep_video_vertex, 4)}</td>
                  <td className="pl-4 text-xs text-slate-400">{fmt(f.unit_costs.vertex_deep_videos)} videos</td>
                </tr>
                <tr>
                  <td className="py-2 text-slate-300">Deep analyses done manually in AI Studio</td>
                  <td className="text-right tabular-nums">$0.00</td>
                  <td className="pl-4 text-xs text-slate-400">{fmt(f.unit_costs.manual_deep_videos)} videos, while Vertex was policy-blocked</td>
                </tr>
                <tr>
                  <td className="py-2 text-slate-300">Per text-tagged video (Tier 2)</td>
                  <td className="text-right tabular-nums">{usd(f.unit_costs.per_tier2_video, 5)}</td>
                  <td />
                </tr>
                {[["Per report", "per_report"], ["Per script", "per_script"], ["Per rendered second", "per_rendered_second"]].map(([l, k]) => (
                  <tr key={k}>
                    <td className="py-2 text-slate-300">{l}</td>
                    <td className="text-right tabular-nums">{usd(f.unit_costs[k])}</td>
                    <td className="pl-4 text-xs text-slate-400">{f.unit_costs[k] === null ? "not started" : ""}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </Card>
          <p className="text-xs text-slate-400">
            {f.note}
            {f.bigquery_scope === "own_jobs_only" &&
              " BigQuery figure covers the scheduler's own queries only (it lacks project-wide job-history access)."}
            {f.bigquery_scope === "last_full_run" &&
              " BigQuery figure is carried from the last full run (the scheduler cannot read job history)."}
          </p>
        </div>
      )}
    </Page>
  );
}
