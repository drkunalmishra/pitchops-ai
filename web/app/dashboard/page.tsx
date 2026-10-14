"use client";

import { useEffect, useState } from "react";
import Nav from "@/components/Nav";
import { apiGet } from "@/lib/api";
import { useUser } from "@/lib/useUser";

type KV = { k: string; n: number };
type Stats = {
  brokers: number;
  companies: number;
  channels: number;
  candidates: number;
  review_queue: number;
  videos: number;
  shorts: number;
  long_form: number;
  quota_units_today: number;
  quota_cap: number;
  gemini_spend_usd_est: number;
  gemini_budget_usd: number;
  gemini_calls: number;
  channels_by_match_type: KV[];
  channels_by_route: KV[];
  as_of: string;
};

const fmt = (n: number) => (n ?? 0).toLocaleString("en-US");

function Tile({ label, value, sub }: { label: string; value: string; sub?: string }) {
  return (
    <div className="rounded-xl border border-navy-700 bg-navy-900 p-5">
      <div className="text-xs font-medium uppercase tracking-wider text-slate-400">{label}</div>
      <div className="mt-2 text-3xl font-semibold tabular-nums text-white">{value}</div>
      {sub && <div className="mt-1 text-xs text-teal-400">{sub}</div>}
    </div>
  );
}

function Breakdown({ title, rows }: { title: string; rows: KV[] }) {
  const max = Math.max(1, ...rows.map((r) => r.n));
  return (
    <div className="rounded-xl border border-navy-700 bg-navy-900 p-5">
      <div className="mb-3 text-xs font-medium uppercase tracking-wider text-slate-400">{title}</div>
      {rows.length === 0 && <div className="text-sm text-slate-500">No data yet</div>}
      <ul className="space-y-2">
        {rows.map((r) => (
          <li key={r.k} className="text-sm">
            <div className="flex justify-between">
              <span className="text-slate-300">{r.k.replaceAll("_", " ")}</span>
              <span className="tabular-nums text-white">{fmt(r.n)}</span>
            </div>
            <div className="mt-1 h-1.5 rounded bg-navy-800">
              <div className="h-1.5 rounded bg-teal-500" style={{ width: `${(100 * r.n) / max}%` }} />
            </div>
          </li>
        ))}
      </ul>
    </div>
  );
}

export default function Dashboard() {
  const user = useUser();
  const [stats, setStats] = useState<Stats | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (user) apiGet<Stats>("/v1/corpus/stats").then(setStats).catch((e) => setError(String(e.message || e)));
  }, [user]);

  if (!user) return null;
  return (
    <main className="mx-auto max-w-6xl px-4 py-8 sm:px-6">
      <Nav user={user} />
      <h1 className="mb-6 text-2xl font-semibold">Corpus dashboard</h1>
      {error && <p className="mb-6 rounded-lg border border-red-900 bg-red-950/40 p-3 text-sm text-red-300">{error}</p>}
      {!stats && !error && <p className="text-slate-400">Loading…</p>}
      {stats && (
        <>
          <section className="grid grid-cols-2 gap-4 md:grid-cols-4">
            <Tile label="Registered brokers" value={fmt(stats.brokers)} sub="DLD registry" />
            <Tile label="Companies" value={fmt(stats.companies)} />
            <Tile label="Accepted channels" value={fmt(stats.channels)} sub={`${fmt(stats.candidates)} candidates`} />
            <Tile label="Review queue" value={fmt(stats.review_queue)} sub="awaiting a decision" />
            <Tile label="Videos" value={fmt(stats.videos)} />
            <Tile label="Shorts / long-form" value={`${fmt(stats.shorts)} / ${fmt(stats.long_form)}`} />
            <Tile label="YouTube quota today" value={fmt(stats.quota_units_today)} sub={`of ${fmt(stats.quota_cap)} units`} />
            <Tile
              label="Gemini spend (est.)"
              value={`$${stats.gemini_spend_usd_est.toFixed(2)}`}
              sub={`of $${stats.gemini_budget_usd} budget · ${fmt(stats.gemini_calls)} calls`}
            />
          </section>
          <section className="mt-4 grid gap-4 md:grid-cols-2">
            <Breakdown title="Channels by match type" rows={stats.channels_by_match_type} />
            <Breakdown title="Channels by discovery route" rows={stats.channels_by_route} />
          </section>
          <p className="mt-6 text-xs text-slate-500">
            As of {new Date(stats.as_of).toLocaleString()} · spend is an estimate from token counts · engagement
            metrics are observed performance, not conversion.
          </p>
        </>
      )}
    </main>
  );
}
