"use client";

import { useCallback, useEffect, useState } from "react";
import Nav from "@/components/Nav";
import { apiGet, apiPost } from "@/lib/api";
import { useUser } from "@/lib/useUser";

type Item = {
  channel_id: string;
  title: string | null;
  handle: string | null;
  thumbnail: string | null;
  url: string;
  company_id: string | null;
  company_name: string | null;
  broker_number: string | null;
  broker_name: string | null;
  match_type: string;
  match_score: number;
  subscribers: number | null;
  videos: number | null;
  routes: string[];
  top_signals: Record<string, number>;
};

export default function Review() {
  const user = useUser();
  const [items, setItems] = useState<Item[] | null>(null);
  const [done, setDone] = useState<Record<string, string>>({});
  const [error, setError] = useState<string | null>(null);

  const load = useCallback(() => {
    apiGet<{ items: Item[] }>("/v1/review/channels?decision=review")
      .then((r) => setItems(r.items))
      .catch((e) => setError(String(e.message || e)));
  }, []);
  useEffect(() => {
    if (user) load();
  }, [user, load]);

  async function decide(it: Item, decision: "manual_accept" | "reject") {
    setDone((d) => ({ ...d, [it.channel_id]: "…" }));
    try {
      await apiPost(`/v1/review/channels/${it.channel_id}`, {
        decision,
        company_id: it.company_id,
        broker_number: it.broker_number,
      });
      setDone((d) => ({ ...d, [it.channel_id]: decision === "manual_accept" ? "accepted" : "rejected" }));
    } catch (e) {
      setDone((d) => ({ ...d, [it.channel_id]: "error" }));
      setError(String((e as Error).message));
    }
  }

  if (!user) return null;
  const open = (items || []).filter((i) => !done[i.channel_id] || done[i.channel_id] === "…");
  return (
    <main className="mx-auto max-w-6xl px-4 py-8 sm:px-6">
      <Nav user={user} />
      <div className="mb-6 flex flex-wrap items-end justify-between gap-2">
        <div>
          <h1 className="text-2xl font-semibold">Channel review queue</h1>
          <p className="mt-1 text-sm text-slate-400">
            Matches scored 0.60–0.80. Accept if the channel belongs to the registry company or broker shown. Decisions
            apply to the corpus on the next discover/harvest run.
          </p>
        </div>
        <div className="text-sm text-slate-400">
          {items ? `${open.length} open · ${Object.values(done).filter((v) => v !== "…").length} decided` : ""}
        </div>
      </div>
      {error && <p className="mb-4 rounded-lg border border-red-900 bg-red-950/40 p-3 text-sm text-red-300">{error}</p>}
      {!items && !error && <p className="text-slate-400">Loading…</p>}
      {items && items.length === 0 && <p className="text-slate-400">Queue is empty.</p>}
      <ul className="space-y-3">
        {(items || []).map((it) => {
          const state = done[it.channel_id];
          return (
            <li
              key={it.channel_id}
              className={`flex flex-col gap-4 rounded-xl border border-navy-700 bg-navy-900 p-4 sm:flex-row sm:items-center ${state && state !== "…" ? "opacity-40" : ""}`}
            >
              <div className="flex min-w-0 flex-1 items-center gap-4">
                {it.thumbnail ? (
                  // eslint-disable-next-line @next/next/no-img-element
                  <img src={it.thumbnail} alt="" className="h-12 w-12 shrink-0 rounded-full" />
                ) : (
                  <div className="h-12 w-12 shrink-0 rounded-full bg-navy-800" />
                )}
                <div className="min-w-0">
                  <a href={it.url} target="_blank" rel="noreferrer" className="font-medium text-white hover:text-teal-400">
                    {it.title || it.channel_id}
                  </a>
                  <div className="truncate text-xs text-slate-400">
                    {it.handle} · {(it.subscribers ?? 0).toLocaleString()} subs · {(it.videos ?? 0).toLocaleString()} videos ·{" "}
                    {it.routes.join(", ")}
                  </div>
                  <div className="mt-1 text-sm">
                    <span className="text-slate-400">→ </span>
                    <span className="text-teal-400">
                      {it.broker_name ? `${it.broker_name} (broker ${it.broker_number})` : it.company_name || it.company_id}
                    </span>
                  </div>
                  <div className="mt-1 flex flex-wrap gap-1">
                    {Object.entries(it.top_signals).map(([k, v]) => (
                      <span key={k} className="rounded bg-navy-800 px-1.5 py-0.5 text-[11px] text-slate-300">
                        {k.replaceAll("_", " ")} {Number(v).toFixed(2)}
                      </span>
                    ))}
                  </div>
                </div>
              </div>
              <div className="flex shrink-0 items-center gap-3">
                <span className="text-lg font-semibold tabular-nums text-white">{it.match_score.toFixed(2)}</span>
                {state && state !== "…" ? (
                  <span className="w-36 text-center text-sm text-slate-300">{state}</span>
                ) : (
                  <>
                    <button
                      onClick={() => decide(it, "manual_accept")}
                      className="rounded-lg bg-teal-500 px-3 py-1.5 text-sm font-semibold text-navy-950 hover:bg-teal-400"
                    >
                      Accept
                    </button>
                    <button
                      onClick={() => decide(it, "reject")}
                      className="rounded-lg border border-navy-700 px-3 py-1.5 text-sm hover:border-red-400 hover:text-red-300"
                    >
                      Reject
                    </button>
                  </>
                )}
              </div>
            </li>
          );
        })}
      </ul>
    </main>
  );
}
