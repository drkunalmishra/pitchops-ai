"use client";

import Link from "next/link";
import { useMemo, useState } from "react";
import { Card, Page, STATUS_STYLE, Status, fmt, human, useApi } from "@/components/ui";

type Row = {
  script_id: string;
  title: string | null;
  property_name: string;
  buyer_persona: string;
  format: string;
  avatar_id: string;
  status: string;
  compliance_status: string;
  version: number;
  duration_est: number | null;
  demo_case?: boolean;
};


const FORMATS: Record<string, string> = { generic: "30–45 s", walkthrough_16x9: "16:9 ≤ 120 s", short_9x16: "9:16 ≤ 55 s" };

export default function StudioPage() {
  const { data, error } = useApi<Row[]>("/v1/scripts");
  const [f, setF] = useState({ q: "", format: "", status: "", compliance: "" });
  const rows = useMemo(
    () =>
      (data || []).filter(
        (r) =>
          (!f.q || `${r.property_name} ${r.title} ${r.buyer_persona}`.toLowerCase().includes(f.q.toLowerCase())) &&
          (!f.format || r.format === f.format) &&
          (!f.status || r.status === f.status) &&
          (!f.compliance || r.compliance_status === f.compliance),
      ),
    [data, f],
  );
  const sel = "rounded-lg border border-navy-700 bg-navy-950 px-2 py-1.5 text-sm text-white";
  return (
    <Page
      title="Script Studio"
      sub="Grounded scripts: every factual line cites fact records; compliance runs on every version; approval freezes the script."
    >
      <Status error={error} loading={!data} />
      {data && (
        <Card>
          <div className="mb-3 flex flex-wrap items-center gap-2">
            <label className="sr-only" htmlFor="sq">Search</label>
            <input id="sq" className={`${sel} w-56`} placeholder="Search property / persona…" value={f.q} onChange={(e) => setF({ ...f, q: e.target.value })} />
            <select aria-label="Format" className={sel} value={f.format} onChange={(e) => setF({ ...f, format: e.target.value })}>
              <option value="">All formats</option>
              {Object.entries(FORMATS).map(([k, v]) => (
                <option key={k} value={k}>{v}</option>
              ))}
            </select>
            <select aria-label="Status" className={sel} value={f.status} onChange={(e) => setF({ ...f, status: e.target.value })}>
              <option value="">All statuses</option>
              {["draft", "approved", "rejected"].map((k) => <option key={k}>{k}</option>)}
            </select>
            <select aria-label="Compliance" className={sel} value={f.compliance} onChange={(e) => setF({ ...f, compliance: e.target.value })}>
              <option value="">All compliance</option>
              {["PASS", "WARN", "BLOCK"].map((k) => <option key={k}>{k}</option>)}
            </select>
            <span className="text-xs text-slate-400">{fmt(rows.length)} of {fmt(data.length)}</span>
          </div>
          <div className="overflow-x-auto">
            <table className="w-full text-left text-sm">
              <thead className="text-xs uppercase tracking-wider text-slate-400">
                <tr>
                  <th className="py-2 pr-3">Script</th>
                  <th className="pr-3">Property</th>
                  <th className="pr-3">Buyer persona</th>
                  <th className="pr-3">Format</th>
                  <th className="pr-3 text-right">Length</th>
                  <th className="pr-3">Compliance</th>
                  <th>Status</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-navy-800">
                {rows.map((r) => (
                  <tr key={r.script_id} className="hover:bg-navy-800/50">
                    <td className="py-2 pr-3">
                      <Link href={`/script/?id=${r.script_id}`} className="font-medium text-white hover:text-teal-400">
                        {r.title || r.script_id}
                      </Link>
                      {r.demo_case && <span className="ml-2 text-xs text-amber-300">demo case</span>}
                      <div className="text-xs text-slate-400">v{r.version} · {r.avatar_id}</div>
                    </td>
                    <td className="pr-3 text-slate-300">{r.property_name}</td>
                    <td className="pr-3 text-slate-300">{human(r.buyer_persona)}</td>
                    <td className="pr-3 text-slate-300">{FORMATS[r.format] || r.format}</td>
                    <td className="pr-3 text-right tabular-nums">{r.duration_est ? `${fmt(r.duration_est)} s` : "—"}</td>
                    <td className="pr-3"><span className={`rounded px-2 py-0.5 text-xs ${STATUS_STYLE[r.compliance_status]}`}>{r.compliance_status}</span></td>
                    <td><span className={`rounded px-2 py-0.5 text-xs ${STATUS_STYLE[r.status]}`}>{r.status}</span></td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
          <p className="mt-3 text-xs text-slate-400">
            Compliance is a prototype decision aid based on DLD guidance and team-defined rules — not legal advice or live
            permit verification. Brand: PitchOps Demo Realty · permit DEMO-PERMIT (demo only).
          </p>
        </Card>
      )}
    </Page>
  );
}
