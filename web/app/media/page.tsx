"use client";

import Link from "next/link";
import { useMemo, useState } from "react";
import { Card, Page, Status, Tile, fmt, human, usd, useApi } from "@/components/ui";

type Plan = {
  plan_id: string;
  property_name: string;
  format: string;
  avatar_id: string;
  state: string;
  est_cost_usd: number;
  est_duration_sec: number;
  preview_duration_sec?: number;
  images_selected: number;
  script_status: string | null;
  preview_qc?: string[];
};
type Resp = { plans: Plan[]; media_budget_usd: number; committed_usd: number; project_spent_usd: number; project_cap_usd: number };

const STATE: Record<string, string> = {
  DRAFT: "bg-navy-800 text-slate-300",
  PREVIEW_READY: "bg-teal-900/70 text-teal-200",
  AWAITING_APPROVAL: "bg-teal-900/70 text-teal-200",
  APPROVED: "bg-teal-500 text-navy-950",
  GENERATING: "bg-amber-900/60 text-amber-200",
  COMPOSING: "bg-amber-900/60 text-amber-200",
  REVIEW: "bg-amber-900/60 text-amber-200",
  DONE: "bg-teal-600 text-white",
  REJECTED: "bg-navy-800 text-slate-500",
  FAILED: "bg-red-900/70 text-red-200",
};

export default function MediaPage() {
  const { data, error } = useApi<Resp>("/v1/media/plans");
  const [fmtF, setFmtF] = useState("");
  const rows = useMemo(() => (data?.plans || []).filter((p) => !fmtF || p.format === fmtF), [data, fmtF]);
  const remaining = data ? data.media_budget_usd - data.committed_usd : 0;
  return (
    <Page title="Media Approvals" sub="Nothing is generated with Veo or Imagen until you approve a plan here, after watching its free preview (D16).">
      <Status error={error} loading={!data} />
      {data && (
        <div className="space-y-6">
          <div className="grid grid-cols-2 gap-4 md:grid-cols-4">
            <Tile label="Media budget" value={usd(data.media_budget_usd, 0)} />
            <Tile label="Committed (approved)" value={usd(data.committed_usd)} />
            <Tile label="Remaining" value={usd(remaining)} sub={remaining < 10 ? "low — approvals may be refused" : undefined} />
            <Tile label="Project spend" value={usd(data.project_spent_usd)} sub={`cap ${usd(data.project_cap_usd, 0)}`} />
          </div>
          <Card>
            <div className="mb-3 flex flex-wrap items-center gap-2 text-sm">
              {[["", "All"], ["16x9", "16:9 walkthroughs"], ["9x16", "9:16 Shorts"]].map(([k, l]) => (
                <button key={k} onClick={() => setFmtF(k)} aria-pressed={fmtF === k} className={`rounded-lg px-3 py-1 ${fmtF === k ? "bg-teal-600 text-white" : "border border-navy-700 text-slate-300"}`}>
                  {l}
                </button>
              ))}
              <Link href="/images/" className="ml-auto text-teal-400 hover:underline">Property images →</Link>
              <Link href="/avatars/" className="text-teal-400 hover:underline">Avatars →</Link>
            </div>
            <div className="overflow-x-auto">
              <table className="w-full text-left text-sm">
                <thead className="text-xs uppercase tracking-wider text-slate-400">
                  <tr>
                    <th className="py-2 pr-3">Property</th>
                    <th className="pr-3">Format</th>
                    <th className="pr-3">Avatar</th>
                    <th className="pr-3 text-right">Images</th>
                    <th className="pr-3 text-right">Length</th>
                    <th className="pr-3 text-right">Veo est.</th>
                    <th className="pr-3">Script</th>
                    <th>State</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-navy-800">
                  {rows.map((p) => (
                    <tr key={p.plan_id} className="hover:bg-navy-800/50">
                      <td className="py-2 pr-3">
                        <Link className="font-medium text-white hover:text-teal-400" href={`/plan/?id=${p.plan_id}`}>{p.property_name}</Link>
                        {!!p.preview_qc?.length && <span className="ml-2 text-xs text-amber-300">QC: {p.preview_qc.join(", ")}</span>}
                      </td>
                      <td className="pr-3 text-slate-300">{p.format === "16x9" ? "16:9" : "9:16"}</td>
                      <td className="pr-3 text-slate-300">{human(p.avatar_id.replace("avatar_", ""))}</td>
                      <td className={`pr-3 text-right tabular-nums ${p.images_selected < 4 ? "text-amber-300" : ""}`}>{p.images_selected}</td>
                      <td className="pr-3 text-right tabular-nums">{fmt(p.preview_duration_sec ?? p.est_duration_sec)} s</td>
                      <td className="pr-3 text-right tabular-nums">{usd(p.est_cost_usd)}</td>
                      <td className="pr-3 text-xs text-slate-300">{p.script_status}</td>
                      <td><span className={`rounded px-2 py-0.5 text-xs ${STATE[p.state] || STATE.DRAFT}`}>{p.state.replace("_", " ")}</span></td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
            <p className="mt-3 text-xs text-slate-400">
              Veo costs are conservative estimates (Veo 3.1 Fast list prices); actual spend is logged per clip. Amber image counts mean
              the property needs more photos — add them on the Property images page.
            </p>
          </Card>
        </div>
      )}
    </Page>
  );
}
