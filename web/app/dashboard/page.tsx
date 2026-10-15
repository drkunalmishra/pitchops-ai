"use client";

import Link from "next/link";
import { Band, Card, Page, Status, Tile, fmt, usd, useApi } from "@/components/ui";

type Overview = {
  funnel: Record<string, number | string>;
  top_personas: Record<string, { persona_id: string; name: string; rating_band: string | null; weighted_evidence: number }>;
  top_property: { property_id: string; canonical_name: string; developer: string; videos: number } | null;
  finops: { total_usd: number; project_cap_usd: number; project_cap_pct: number; projected_total_usd: number; as_of: string };
};

const STEPS: [string, string][] = [
  ["brokers", "DLD registered brokers"],
  ["companies", "Brokerage companies"],
  ["channels", "YouTube channels matched"],
  ["relevant_channels", "Relevant channels (UAE real estate)"],
  ["videos", "Videos harvested"],
  ["relevant_videos", "Relevant videos, last 24 months"],
  ["deep_selected", "Selected for deep analysis (top 10 trending × ~50 companies)"],
  ["deep_analysed", "Deep-analysed (four tables)"],
  ["comments", "Comments collected (PII redacted)"],
];

export default function OverviewPage() {
  const { data, error } = useApi<Overview>("/v1/explore/overview");
  const f = data?.funnel || {};
  const first = Number(f.brokers || 1);
  return (
    <Page title="Overview" sub="From registered brokers' public YouTube content to an evidence-rated persona playbook.">
      <Status error={error} loading={!data} />
      {data && (
        <div className="grid gap-6 lg:grid-cols-3">
          <Card title="Corpus funnel" className="lg:col-span-2">
            <ol className="space-y-2.5">
              {STEPS.map(([k, label]) => {
                const n = Number(f[k] || 0);
                const w = Math.max(1.5, (100 * Math.log10(1 + n)) / Math.log10(1 + Math.max(first, Number(f.videos || 1))));
                return (
                  <li key={k} className="text-sm">
                    <div className="flex justify-between gap-3">
                      <span className="text-slate-300">{label}</span>
                      <span className="tabular-nums font-medium text-white">{fmt(n)}</span>
                    </div>
                    <div className="mt-1 h-2 rounded bg-navy-800">
                      <div className="h-2 rounded bg-teal-500" style={{ width: `${w}%` }} />
                    </div>
                  </li>
                );
              })}
            </ol>
            <p className="mt-3 text-xs text-slate-400">Bar length on a log scale so every stage stays visible.</p>
          </Card>
          <div className="grid gap-4">
            <Tile
              label="Top seller persona"
              value={<span className="text-lg">{data.top_personas.seller?.name ?? "—"}</span>}
              sub={<Band band={data.top_personas.seller?.rating_band} confidence={1} />}
            />
            <Tile
              label="Top buyer persona"
              value={<span className="text-lg">{data.top_personas.buyer?.name ?? "—"}</span>}
              sub={<Band band={data.top_personas.buyer?.rating_band} confidence={1} />}
            />
            <Tile
              label="Most-discussed project"
              value={
                data.top_property ? (
                  <Link className="text-lg hover:text-teal-400" href={`/property/?id=${data.top_property.property_id}`}>
                    {data.top_property.canonical_name}
                  </Link>
                ) : (
                  "—"
                )
              }
              sub={data.top_property && `${data.top_property.developer ?? ""} · ${fmt(data.top_property.videos)} videos`}
            />
            <Tile label="Avg sales pressure" value={`${fmt(Number(f.avg_sales_pressure), 1)} / 10`} sub="deep-analysed videos" />
            <Link href="/finops/" className="block">
              <Tile
                label="Spend to date (estimate)"
                value={usd(data.finops.total_usd)}
                sub={`${fmt(data.finops.project_cap_pct, 1)}% of the ${usd(data.finops.project_cap_usd, 0)} project cap`}
              />
            </Link>
          </div>
          <p className="text-xs text-slate-400 lg:col-span-3">
            Last metrics refresh {f.last_refresh ? new Date(String(f.last_refresh)).toLocaleString() : "—"}. Only
            relevant content is shown (UAE real estate, last 24 months). Engagement is reported as OPI / trending,
            never as conversion.
          </p>
        </div>
      )}
    </Page>
  );
}
