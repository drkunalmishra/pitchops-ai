"use client";

import { Card, Page, Pill, Status, Tile, VideoCard, compact, fmt, human, useApi, useParam, type Video } from "@/components/ui";

type Detail = {
  property: {
    canonical_name: string;
    kind: string;
    developer: string | null;
    area: string | null;
    emirate: string | null;
    aliases: string[];
    property_types: string[];
    videos: number;
    recent_videos: number;
    companies: number;
    channels: number;
    total_views: number;
    avg_sales_pressure: number | null;
    top_buyer_personas: string[];
    top_frameworks: string[];
    price_texts: string[];
    media_candidate: string | null;
  };
  videos: Video[];
};

export default function PropertyPage() {
  const id = useParam("id");
  const { data, error } = useApi<Detail>(id ? `/v1/explore/properties/${encodeURIComponent(id)}` : null);
  const p = data?.property;
  return (
    <Page title={p?.canonical_name || "Property"} sub={p && [p.developer, p.area, p.emirate].filter(Boolean).join(" · ")}>
      <Status error={error} loading={!data} />
      {p && data && (
        <div className="space-y-6">
          <div className="grid grid-cols-2 gap-4 md:grid-cols-5">
            <Tile label="Videos" value={fmt(p.videos)} sub={`${fmt(p.recent_videos)} in the last 6 months`} />
            <Tile label="Companies" value={fmt(p.companies)} sub={`${fmt(p.channels)} channels`} />
            <Tile label="Views" value={compact(p.total_views)} />
            <Tile label="Avg sales pressure" value={fmt(p.avg_sales_pressure, 1)} sub="deep-analysed videos" />
            <Tile
              label="Media candidate"
              value={p.media_candidate ? (p.media_candidate === "walkthrough" ? "16:9 walkthrough" : "9:16 Short") : "No"}
              sub={p.kind}
            />
          </div>
          <div className="grid gap-6 lg:grid-cols-3">
            <Card title="Evidence videos" className="lg:col-span-2">
              <div className="space-y-2">
                {data.videos.map((v) => (
                  <VideoCard key={v.video_id} v={v} />
                ))}
              </div>
            </Card>
            <div className="space-y-6">
              {[
                ["Top buyer personas", p.top_buyer_personas],
                ["Top sales frameworks", p.top_frameworks],
                ["Property types", p.property_types],
              ].map(([t, xs]) => (
                <Card key={t as string} title={t as string}>
                  <div className="flex flex-wrap gap-1">
                    {((xs as string[]) || []).map((x) => (
                      <Pill key={x}>{human(x)}</Pill>
                    ))}
                  </div>
                </Card>
              ))}
              <Card title="Prices mentioned (unverified)">
                <ul className="space-y-1 text-sm text-slate-300">
                  {(p.price_texts || []).slice(0, 8).map((x) => (
                    <li key={x}>{x}</li>
                  ))}
                  {!p.price_texts?.length && <li className="text-slate-400">None captured</li>}
                </ul>
              </Card>
              <Card title="Also known as">
                <p className="text-sm text-slate-300">{(p.aliases || []).join(" · ")}</p>
              </Card>
            </div>
          </div>
        </div>
      )}
    </Page>
  );
}
