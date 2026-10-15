"use client";

import Link from "next/link";
import { useState } from "react";
import { Card, Page, Status, compact, fmt, human, useApi } from "@/components/ui";

type Company = {
  company_id: string;
  name: string;
  brokers: number;
  videos: number;
  shorts: number;
  views: number | null;
  deep: number;
  sales_pressure: number | null;
  shortlist_rank: number | null;
  top_buyer: string | null;
  report_type: "full" | "light";
};

export default function CompaniesPage() {
  const { data, error } = useApi<Company[]>("/v1/explore/companies");
  const [q, setQ] = useState("");
  const [onlyFull, setOnlyFull] = useState(false);
  const rows = (data || []).filter(
    (c) => (!onlyFull || c.report_type === "full") && (!q || c.name.toLowerCase().includes(q.toLowerCase())),
  );
  return (
    <Page title="Companies" sub="Relevant brokerages with YouTube presence. Full reports for the deep-analysis shortlist; light reports for the rest.">
      <Status error={error} loading={!data} />
      {data && (
        <Card>
          <div className="mb-3 flex flex-wrap items-center gap-3 text-sm">
            <label className="sr-only" htmlFor="q">
              Search companies
            </label>
            <input
              id="q"
              value={q}
              onChange={(e) => setQ(e.target.value)}
              placeholder="Search companies…"
              className="w-64 rounded-lg border border-navy-700 bg-navy-950 px-3 py-1.5 text-white placeholder:text-slate-500"
            />
            <label className="flex items-center gap-2 text-slate-300">
              <input type="checkbox" checked={onlyFull} onChange={(e) => setOnlyFull(e.target.checked)} />
              Full reports only
            </label>
            <span className="text-xs text-slate-400">
              {fmt(rows.length)} of {fmt(data.length)}
            </span>
          </div>
          <div className="overflow-x-auto">
            <table className="w-full text-left text-sm">
              <thead className="text-xs uppercase tracking-wider text-slate-400">
                <tr>
                  <th className="py-2 pr-3">Company</th>
                  <th className="pr-3">Report</th>
                  <th className="pr-3 text-right">Videos</th>
                  <th className="pr-3 text-right">Views</th>
                  <th className="pr-3 text-right">Deep</th>
                  <th className="pr-3 text-right">Sales pressure</th>
                  <th>Top buyer persona</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-navy-800">
                {rows.slice(0, 300).map((c) => (
                  <tr key={c.company_id} className="hover:bg-navy-800/50">
                    <td className="py-2 pr-3">
                      <Link href={`/company/?id=${c.company_id}`} className="font-medium text-white hover:text-teal-400">
                        {c.name}
                      </Link>
                    </td>
                    <td className="pr-3 text-xs">
                      <span className={c.report_type === "full" ? "text-teal-400" : "text-slate-400"}>{c.report_type}</span>
                    </td>
                    <td className="pr-3 text-right tabular-nums">{fmt(c.videos)}</td>
                    <td className="pr-3 text-right tabular-nums">{compact(c.views)}</td>
                    <td className="pr-3 text-right tabular-nums">{fmt(c.deep)}</td>
                    <td className="pr-3 text-right tabular-nums">{fmt(c.sales_pressure, 1)}</td>
                    <td className="text-slate-300">{c.top_buyer ? human(c.top_buyer) : "—"}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </Card>
      )}
    </Page>
  );
}
