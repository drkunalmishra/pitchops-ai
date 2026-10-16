"use client";

import { Bars, Card, CitedLine, Page, Status, Tile, VideoCard, compact, fmt, human, useApi, useParam, type Cited, type Video } from "@/components/ui";

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
  report: {
    report_type: string;
    model_id: string;
    markdown: string;
    report: {
      headline: string;
      persona_statement: Cited;
      funnel: { awareness: Cited; consideration: Cited; decision: Cited };
      strengths: Cited[];
      gaps: Cited[];
      opportunities: Cited[];
    };
  } | null;
};

function download(name: string, md: string) {
  const a = document.createElement("a");
  a.href = URL.createObjectURL(new Blob([md], { type: "text/markdown" }));
  a.download = `${name.replace(/[^a-z0-9]+/gi, "_")}_report.md`;
  a.click();
  URL.revokeObjectURL(a.href);
}

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
          {data.report ? (
            <Card title={`Report — internal draft (${data.report.report_type}, ${data.report.model_id})`}>
              <div className="flex flex-wrap items-start justify-between gap-3">
                <p className="text-base font-medium text-white">{data.report.report.headline}</p>
                <button
                  onClick={() => download(c.name, data.report!.markdown)}
                  className="rounded-lg border border-navy-700 px-3 py-1 text-xs text-slate-200 hover:border-teal-500"
                >
                  Download Markdown
                </button>
              </div>
              <div className="mt-3 grid gap-4 text-sm text-slate-200 md:grid-cols-2">
                <div>
                  <div className="text-xs font-semibold uppercase tracking-wider text-slate-400">Persona statement</div>
                  <p className="mt-1"><CitedLine c={data.report.report.persona_statement} /></p>
                  <div className="mt-3 text-xs font-semibold uppercase tracking-wider text-slate-400">Funnel</div>
                  <ul className="mt-1 space-y-1">
                    {(["awareness", "consideration", "decision"] as const).map((k) => (
                      <li key={k}>
                        <b className="text-slate-300">{human(k)}:</b> <CitedLine c={data.report!.report.funnel[k]} />
                      </li>
                    ))}
                  </ul>
                </div>
                <div className="space-y-3">
                  {(["strengths", "gaps", "opportunities"] as const).map((k) => (
                    <div key={k}>
                      <div className="text-xs font-semibold uppercase tracking-wider text-slate-400">{human(k)}</div>
                      <ul className="mt-1 list-disc space-y-1 pl-4">
                        {data.report!.report[k].map((x, i) => (
                          <li key={i}><CitedLine c={x} /></li>
                        ))}
                      </ul>
                    </div>
                  ))}
                </div>
              </div>
            </Card>
          ) : (
            <Card title="Persona statement">
              <p className="text-sm leading-relaxed text-slate-200">
                Mostly sells with <b>{top("seller")}</b> tactics to <b>{top("buyer")}</b> buyers, typically as{" "}
                <b>{top("format")}</b> videos. Based on {fmt(c.videos)} relevant videos
                {c.deep ? `, ${fmt(c.deep)} of them deep-analysed` : " (text tags only)"}.
              </p>
            </Card>
          )}
          <div className="grid gap-6 md:grid-cols-3">
            {(["seller", "buyer", "format"] as const).map((l) => (
              <Card key={l} title={`${l === "format" ? "Formats" : `${human(l)} personas`} (weighted videos)`}>
                <Bars rows={data.mix[l] || []} value={(r) => r.w} label={(r) => human(r.code)} format={(n) => fmt(n, 1)} />
              </Card>
            ))}
          </div>
          {data.gaps.length > 0 && (
            <Card title="Rule-based gaps vs the corpus">
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
