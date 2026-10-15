"use client";

import Link from "next/link";
import { useState } from "react";
import { Card, Page, Status, compact, fmt, human, useApi } from "@/components/ui";

type Property = {
  property_id: string;
  rank: number;
  canonical_name: string;
  kind: string;
  developer: string | null;
  area: string | null;
  emirate: string | null;
  property_types: string[];
  videos: number;
  recent_videos: number;
  companies: number;
  total_views: number;
  avg_sales_pressure: number | null;
  top_buyer_personas: string[];
  top_frameworks: string[];
  price_texts: string[];
  example_video_ids: string[];
  media_candidate: string | null;
};

export default function PropertiesPage() {
  const { data, error } = useApi<Property[]>("/v1/explore/properties?limit=80");
  const [kind, setKind] = useState<"project" | "all">("project");
  const rows = (data || []).filter((p) => kind === "all" || p.kind === "project").slice(0, 60);
  return (
    <Page title="Property Intelligence" sub="Most-discussed projects across relevant broker videos, ranked by videos, companies, reach and recency.">
      <Status error={error} loading={!data} />
      {data && (
        <Card>
          <div className="mb-3 flex gap-2 text-sm" role="radiogroup" aria-label="Show">
            {(["project", "all"] as const).map((k) => (
              <button
                key={k}
                role="radio"
                aria-checked={kind === k}
                onClick={() => setKind(k)}
                className={`rounded-lg px-3 py-1 ${kind === k ? "bg-teal-600 text-white" : "border border-navy-700 text-slate-300"}`}
              >
                {k === "project" ? "Projects only" : "Include communities / landmarks"}
              </button>
            ))}
          </div>
          <div className="overflow-x-auto">
            <table className="w-full text-left text-sm">
              <thead className="text-xs uppercase tracking-wider text-slate-400">
                <tr>
                  <th className="py-2 pr-3">#</th>
                  <th className="pr-3">Property</th>
                  <th className="pr-3">Developer</th>
                  <th className="pr-3">Area</th>
                  <th className="pr-3 text-right">Videos</th>
                  <th className="pr-3 text-right">Companies</th>
                  <th className="pr-3 text-right">Views</th>
                  <th className="pr-3 text-right" title="Videos in the last 6 months">Recent</th>
                  <th className="pr-3">Top buyer personas</th>
                  <th>Media</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-navy-800">
                {rows.map((p, i) => (
                  <tr key={p.property_id} className="hover:bg-navy-800/50">
                    <td className="py-2 pr-3 tabular-nums text-slate-400">{i + 1}</td>
                    <td className="pr-3">
                      <Link href={`/property/?id=${p.property_id}`} className="font-medium text-white hover:text-teal-400">
                        {p.canonical_name}
                      </Link>
                      {p.kind !== "project" && <span className="ml-2 text-xs text-slate-400">{p.kind}</span>}
                    </td>
                    <td className="pr-3 text-slate-300">{p.developer || "—"}</td>
                    <td className="pr-3 text-slate-300">
                      {p.area || "—"}
                      {p.emirate && p.emirate !== "Dubai" ? `, ${p.emirate}` : ""}
                    </td>
                    <td className="pr-3 text-right tabular-nums">{fmt(p.videos)}</td>
                    <td className="pr-3 text-right tabular-nums">{fmt(p.companies)}</td>
                    <td className="pr-3 text-right tabular-nums">{compact(p.total_views)}</td>
                    <td className="pr-3 text-right tabular-nums">{fmt(p.recent_videos)}</td>
                    <td className="pr-3 text-xs text-slate-300">{(p.top_buyer_personas || []).slice(0, 2).map(human).join(", ")}</td>
                    <td className="text-xs text-teal-400">{p.media_candidate ? (p.media_candidate === "walkthrough" ? "16:9" : "Short") : ""}</td>
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
