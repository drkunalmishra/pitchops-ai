"use client";

import { Bars, Card, Page, Status, Tile, VideoCard, compact, fmt, human, useApi, useParam, type Video } from "@/components/ui";

type Mix = { code: string; w: number; n: number };
type Detail = {
  company: {
    name: string;
    brokers: number;
    videos: number;
    shorts: number;
    views: number | null;
    deep: number;
    sales_pressure: number | null;
    shortlist_rank: number | null;
    top_buyer: string | null;
    report_type: string;
  };
  channels: { channel_id: string; title: string; handle: string | null; subscriber_count: number | null; relevant_video_count: number | null }[];
  videos: Video[];
  mix: Record<string, Mix[]>;
  gaps: string[];
  corpus: { sales_pressure: number | null };
};

export default function CompanyPage() {
  const id = useParam("id");
  const { data, error } = useApi<Detail>(id ? `/v1/explore/companies/${encodeURIComponent(id)}` : null);
  const c = data?.company;
  const top = (layer: string) => human(data?.mix[layer]?.[0]?.code);
  return (
    <Page
      title={c?.name || "Company"}
      sub={c && `${c.report_type === "full" ? `Full report · shortlist #${c.shortlist_rank}` : "Light report (text tags + metrics)"}`}
    >
      <Status error={error} loading={!data} />
      {c && data && (
        <div className="space-y-6">
          <div className="grid grid-cols-2 gap-4 md:grid-cols-5">
            <Tile label="Relevant videos" value={fmt(c.videos)} sub={`${fmt(c.shorts)} Shorts`} />
            <Tile label="Views" value={compact(c.views)} />
            <Tile label="Deep-analysed" value={fmt(c.deep)} />
            <Tile label="Sales pressure" value={fmt(c.sales_pressure, 1)} sub={`corpus ${fmt(data.corpus.sales_pressure, 1)}`} />
            <Tile label="Registered brokers" value={fmt(c.brokers)} />
          </div>
          <Card title="Persona statement">
            <p className="text-sm leading-relaxed text-slate-200">
              Mostly sells with <b>{top("seller")}</b> tactics to <b>{top("buyer")}</b> buyers, typically as{" "}
              <b>{top("format")}</b> videos. Based on {fmt(c.videos)} relevant videos
              {c.deep ? `, ${fmt(c.deep)} of them deep-analysed` : " (text tags only)"}.
            </p>
          </Card>
          <div className="grid gap-6 md:grid-cols-3">
            {(["seller", "buyer", "format"] as const).map((l) => (
              <Card key={l} title={`${l === "format" ? "Formats" : `${human(l)} personas`} (weighted videos)`}>
                <Bars rows={data.mix[l] || []} value={(r) => r.w} label={(r) => human(r.code)} format={(n) => fmt(n, 1)} />
              </Card>
            ))}
          </div>
          {data.gaps.length > 0 && (
            <Card title="Gaps vs the corpus">
              <ul className="list-disc space-y-1 pl-5 text-sm text-slate-200">
                {data.gaps.map((g) => (
                  <li key={g}>{g}</li>
                ))}
              </ul>
            </Card>
          )}
          <div className="grid gap-6 lg:grid-cols-3">
            <Card title="Top videos (deep-analysed first, then trending)" className="lg:col-span-2">
              <div className="space-y-2">
                {data.videos.map((v) => (
                  <VideoCard key={v.video_id} v={v} />
                ))}
              </div>
            </Card>
            <Card title="Channels">
              <ul className="space-y-2 text-sm">
                {data.channels.map((ch) => (
                  <li key={ch.channel_id}>
                    <a className="text-white hover:text-teal-400" href={`https://www.youtube.com/channel/${ch.channel_id}`} target="_blank" rel="noreferrer">
                      {ch.title}
                    </a>
                    <div className="text-xs text-slate-400">
                      {compact(ch.subscriber_count)} subscribers · {fmt(ch.relevant_video_count)} relevant videos
                    </div>
                  </li>
                ))}
              </ul>
            </Card>
          </div>
        </div>
      )}
    </Page>
  );
}
