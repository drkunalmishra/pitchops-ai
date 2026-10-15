"use client";

import Link from "next/link";
import { useState } from "react";
import { Card, Page, Status, fmt, useApi } from "@/components/ui";
import { apiPost } from "@/lib/api";

type QA = {
  videos: { video_id: string; title: string; relevance_reason: string | null; relevance_source: string | null; channel_relevant: boolean | null }[];
  channels: { channel_id: string; title: string; irrelevant_share: number | null; relevant_video_count: number | null; relevance_reason: string | null }[];
  needs_review: { video_id: string; model_id: string; error: string | null; ingested_at: string }[];
};

export default function AdminPage() {
  const { data, error } = useApi<QA>("/v1/admin/qa");
  const [done, setDone] = useState<Record<string, string>>({});
  const mark = async (id: string) => {
    if (!window.confirm("Mark this video relevant? It will re-enter analysis on the next aggregation run.")) return;
    try {
      await apiPost(`/v1/admin/relevance/${id}`, { is_relevant: true });
      setDone((d) => ({ ...d, [id]: "marked relevant" }));
    } catch (e: any) {
      setDone((d) => ({ ...d, [id]: `error: ${e.message}` }));
    }
  };
  return (
    <Page title="Admin / QA" sub="Flagged (never deleted) content and analyses that need review. Overrides are written as relevance_source = manual.">
      <Status error={error} loading={!data} />
      {data && (
        <div className="space-y-6">
          <Card title={`Needs review (${data.needs_review.length})`}>
            {data.needs_review.length === 0 ? (
              <p className="text-sm text-slate-400">Nothing waiting.</p>
            ) : (
              <ul className="space-y-1 text-sm">
                {data.needs_review.map((r) => (
                  <li key={r.video_id}>
                    <Link className="text-white hover:text-teal-400" href={`/video/?id=${r.video_id}`}>{r.video_id}</Link>{" "}
                    <span className="text-slate-400">{r.error}</span>
                  </li>
                ))}
              </ul>
            )}
          </Card>
          <Card title={`Irrelevant videos in window (showing ${fmt(data.videos.length)})`}>
            <div className="overflow-x-auto">
              <table className="w-full text-left text-sm">
                <thead className="text-xs uppercase tracking-wider text-slate-400">
                  <tr>
                    <th className="py-2 pr-3">Video</th>
                    <th className="pr-3">Source</th>
                    <th className="pr-3">Reason</th>
                    <th />
                  </tr>
                </thead>
                <tbody className="divide-y divide-navy-800">
                  {data.videos.map((v) => (
                    <tr key={v.video_id}>
                      <td className="py-2 pr-3">
                        <Link className="text-white hover:text-teal-400" href={`/video/?id=${v.video_id}`}>{v.title}</Link>
                        {v.channel_relevant === false && <span className="ml-2 text-xs text-slate-400">(channel flagged)</span>}
                      </td>
                      <td className="pr-3 text-slate-300">{v.relevance_source}</td>
                      <td className="pr-3 text-xs text-slate-300">{v.relevance_reason}</td>
                      <td className="whitespace-nowrap text-right">
                        {done[v.video_id] ? (
                          <span className="text-xs text-teal-400">{done[v.video_id]}</span>
                        ) : (
                          <button onClick={() => mark(v.video_id)} className="rounded-lg border border-navy-700 px-2 py-1 text-xs text-slate-200 hover:border-teal-500">
                            Mark relevant
                          </button>
                        )}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </Card>
          <Card title={`Irrelevant channels (${fmt(data.channels.length)})`}>
            <ul className="space-y-1 text-sm">
              {data.channels.map((c) => (
                <li key={c.channel_id}>
                  <a className="text-white hover:text-teal-400" href={`https://www.youtube.com/channel/${c.channel_id}`} target="_blank" rel="noreferrer">{c.title}</a>{" "}
                  <span className="text-xs text-slate-400">
                    {c.irrelevant_share === null ? "" : `${fmt(100 * c.irrelevant_share)}% irrelevant · `}
                    {fmt(c.relevant_video_count)} relevant · {c.relevance_reason}
                  </span>
                </li>
              ))}
            </ul>
          </Card>
        </div>
      )}
    </Page>
  );
}
