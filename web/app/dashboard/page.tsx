"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { onAuthStateChanged, signOut, type User } from "firebase/auth";
import { apiGet, auth } from "@/lib/firebase";

type Stats = {
  brokers: number;
  companies: number;
  channels: number;
  videos: number;
  shorts: number;
  quota_units_today: number;
  quota_cap: number;
  gemini_spend_usd_est: number;
  gemini_budget_usd: number;
  gemini_calls: number;
  as_of: string;
};

const fmt = (n: number) => n.toLocaleString("en-US");

function Tile({ label, value, sub }: { label: string; value: string; sub?: string }) {
  return (
    <div className="rounded-xl border border-navy-700 bg-navy-900 p-5">
      <div className="text-xs font-medium uppercase tracking-wider text-slate-400">{label}</div>
      <div className="mt-2 text-3xl font-semibold tabular-nums text-white">{value}</div>
      {sub && <div className="mt-1 text-xs text-teal-400">{sub}</div>}
    </div>
  );
}

export default function Dashboard() {
  const router = useRouter();
  const [user, setUser] = useState<User | null>(null);
  const [stats, setStats] = useState<Stats | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(
    () =>
      onAuthStateChanged(auth, (u) => {
        if (!u) return router.replace("/");
        setUser(u);
        apiGet<Stats>("/v1/corpus/stats").then(setStats).catch((e) => setError(String(e.message || e)));
      }),
    [router],
  );

  if (!user) return null;
  return (
    <main className="mx-auto max-w-6xl px-4 py-8 sm:px-6">
      <header className="mb-8 flex flex-wrap items-center justify-between gap-4">
        <div>
          <div className="text-sm font-semibold tracking-widest text-teal-400">PITCHOPS AI</div>
          <h1 className="mt-1 text-2xl font-semibold">Corpus dashboard</h1>
        </div>
        <div className="flex items-center gap-3 text-sm text-slate-400">
          <span className="truncate">{user.email}</span>
          <button
            onClick={() => signOut(auth)}
            className="rounded-lg border border-navy-700 px-3 py-1.5 hover:border-teal-500 hover:text-white"
          >
            Sign out
          </button>
        </div>
      </header>
      {error && <p className="mb-6 rounded-lg border border-red-900 bg-red-950/40 p-3 text-sm text-red-300">{error}</p>}
      {!stats && !error && <p className="text-slate-400">Loading…</p>}
      {stats && (
        <>
          <section className="grid grid-cols-2 gap-4 md:grid-cols-4">
            <Tile label="Registered brokers" value={fmt(stats.brokers)} sub="DLD registry" />
            <Tile label="Companies" value={fmt(stats.companies)} />
            <Tile label="Channels" value={fmt(stats.channels)} />
            <Tile label="Videos" value={fmt(stats.videos)} sub="long-form + Shorts" />
            <Tile label="Shorts" value={fmt(stats.shorts)} />
            <Tile
              label="YouTube quota today"
              value={fmt(stats.quota_units_today)}
              sub={`of ${fmt(stats.quota_cap)} units`}
            />
            <Tile
              label="Gemini spend (est.)"
              value={`$${stats.gemini_spend_usd_est.toFixed(2)}`}
              sub={`of $${stats.gemini_budget_usd} budget · ${fmt(stats.gemini_calls)} calls`}
            />
          </section>
          <p className="mt-6 text-xs text-slate-500">
            As of {new Date(stats.as_of).toLocaleString()} · spend is an estimate from token counts.
          </p>
        </>
      )}
    </main>
  );
}
