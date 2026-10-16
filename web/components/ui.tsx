"use client";

import Link from "next/link";
import { useEffect, useState, type ReactNode } from "react";
import Nav from "@/components/Nav";
import { apiGet } from "@/lib/api";
import { useUser } from "@/lib/useUser";

export const fmt = (n: number | null | undefined, d = 0) =>
  n === null || n === undefined ? "—" : Number(n).toLocaleString("en-US", { maximumFractionDigits: d });

export const compact = (n: number | null | undefined) =>
  n === null || n === undefined ? "—" : Intl.NumberFormat("en-US", { notation: "compact" }).format(n);

export const usd = (n: number | null | undefined, d = 2) => (n === null || n === undefined ? "—" : `$${fmt(n, d)}`);

/** "seller:fomo_scarcity" / "end_user_family|both" -> "Fomo Scarcity" / "End User Family" */
export const human = (code: string | null | undefined) =>
  (code || "")
    .split(":")
    .pop()!
    .split("|")[0]
    .replaceAll("_", " ")
    .replace(/\b\w/g, (c) => c.toUpperCase());

export const mmss = (s: number | null | undefined) => {
  if (s === null || s === undefined) return "—";
  const v = Math.round(Number(s));
  return `${Math.floor(v / 60)}:${String(v % 60).padStart(2, "0")}`;
};

export function useApi<T>(path: string | null) {
  const user = useUser();
  const [data, setData] = useState<T | null>(null);
  const [error, setError] = useState<string | null>(null);
  useEffect(() => {
    if (!user || !path) return;
    setData(null);
    setError(null);
    apiGet<T>(path)
      .then(setData)
      .catch((e) => setError(String(e.message || e)));
  }, [user, path]);
  return { user, data, error };
}

export function Page({ title, sub, children }: { title: string; sub?: ReactNode; children: ReactNode }) {
  const user = useUser();
  if (!user) return null;
  return (
    <main className="mx-auto max-w-7xl px-4 py-8 sm:px-6">
      <Nav user={user} />
      <h1 className="text-2xl font-semibold text-white">{title}</h1>
      {sub && <p className="mt-1 text-sm text-slate-400">{sub}</p>}
      <div className="mt-6">{children}</div>
    </main>
  );
}

export function Status({ error, loading }: { error: string | null; loading: boolean }) {
  if (error)
    return (
      <p role="alert" className="rounded-lg border border-red-900 bg-red-950/40 p-3 text-sm text-red-300">
        {error}
      </p>
    );
  if (loading) return <p className="text-slate-400">Loading…</p>;
  return null;
}

export function Card({ title, children, className = "" }: { title?: string; children: ReactNode; className?: string }) {
  return (
    <section className={`rounded-xl border border-navy-700 bg-navy-900 p-5 ${className}`}>
      {title && <h2 className="mb-3 text-xs font-semibold uppercase tracking-wider text-slate-400">{title}</h2>}
      {children}
    </section>
  );
}

export function Tile({ label, value, sub }: { label: string; value: ReactNode; sub?: ReactNode }) {
  return (
    <div className="rounded-xl border border-navy-700 bg-navy-900 p-4">
      <div className="text-xs font-medium uppercase tracking-wider text-slate-400">{label}</div>
      <div className="mt-1.5 text-2xl font-semibold tabular-nums text-white">{value}</div>
      {sub && <div className="mt-1 text-xs text-slate-400">{sub}</div>}
    </div>
  );
}

const BAND: Record<string, string> = {
  A: "bg-teal-400 text-navy-950",
  B: "bg-teal-600 text-white",
  C: "bg-navy-700 text-white",
  D: "bg-navy-800 text-slate-300",
  E: "bg-navy-800 text-slate-400",
};

export function Band({ band, confidence }: { band?: string | null; confidence?: number | null }) {
  if (!band) return <span className="text-xs text-slate-500">no band</span>;
  const low = (confidence ?? 0) < 0.4;
  return (
    <span
      title={`Rating band ${band} · confidence ${fmt(confidence, 2)}${low ? " (low — shown for reference)" : ""}`}
      className={`inline-flex items-center gap-1 rounded-md px-2 py-0.5 text-xs font-semibold ${BAND[band] || BAND.E} ${low ? "opacity-60" : ""}`}
    >
      Band {band}
    </span>
  );
}

/** Horizontal single-series bars (one hue; the title names the series). */
export function Bars({
  rows,
  value = (r) => r.n,
  label = (r) => r.k,
  format = (n) => fmt(n),
  cap,
}: {
  rows: any[];
  value?: (r: any) => number;
  label?: (r: any) => ReactNode;
  format?: (n: number) => string;
  cap?: number;
}) {
  const max = Math.max(1e-9, cap ?? 0, ...rows.map(value));
  return (
    <ul className="space-y-2">
      {rows.map((r, i) => (
        <li key={i} className="text-sm" title={`${typeof label(r) === "string" ? label(r) : ""} ${format(value(r))}`}>
          <div className="flex justify-between gap-3">
            <span className="truncate text-slate-300">{label(r)}</span>
            <span className="tabular-nums text-white">{format(value(r))}</span>
          </div>
          <div className="relative mt-1 h-2 rounded bg-navy-800">
            <div className="h-2 rounded bg-teal-500" style={{ width: `${Math.min(100, (100 * value(r)) / max)}%` }} />
            {cap !== undefined && <div className="absolute inset-y-[-3px] right-0 w-0.5 bg-slate-400" title={`cap ${format(cap)}`} />}
          </div>
        </li>
      ))}
    </ul>
  );
}

export function Pill({ children }: { children: ReactNode }) {
  return <span className="rounded-full border border-navy-700 px-2 py-0.5 text-xs text-slate-300">{children}</span>;
}

export type Video = {
  video_id: string;
  title: string;
  duration_sec: number;
  is_short: boolean;
  channel: string;
  views: number | null;
  trending: number | null;
  deep: boolean;
  claims: { ts_sec: number; quote: string; claim_type: string; has_source: boolean; is_risky: boolean }[] | null;
  hook_text: string | null;
  hook_type: string | null;
  cta_type: string | null;
  summary: string | null;
  sales_pressure_score: number | null;
};

export const yt = (id: string, ts?: number) => `https://www.youtube.com/watch?v=${id}${ts ? `&t=${Math.floor(ts)}s` : ""}`;

export function VideoCard({ v }: { v: Video }) {
  return (
    <article className="flex gap-3 rounded-lg border border-navy-700 bg-navy-950/60 p-3">
      <a href={yt(v.video_id)} target="_blank" rel="noreferrer" className="shrink-0">
        <img
          src={`https://i.ytimg.com/vi/${v.video_id}/mqdefault.jpg`}
          alt={`Thumbnail: ${v.title}`}
          className="h-20 w-36 rounded object-cover"
          loading="lazy"
        />
      </a>
      <div className="min-w-0 flex-1 text-sm">
        <Link href={`/video/?id=${v.video_id}`} className="line-clamp-2 font-medium text-white hover:text-teal-400">
          {v.title}
        </Link>
        <div className="mt-0.5 text-xs text-slate-400">
          {v.channel} · {compact(v.views)} views · {mmss(v.duration_sec)}
          {v.deep && <span className="ml-2 text-teal-400">deep-analysed</span>}
          {v.sales_pressure_score !== null && <span className="ml-2">pressure {fmt(v.sales_pressure_score, 1)}/10</span>}
        </div>
        {v.hook_text && <div className="mt-1 text-xs italic text-slate-300">“{v.hook_text}”</div>}
        {(v.claims || []).slice(0, 2).map((c, i) => (
          <a key={i} href={yt(v.video_id, c.ts_sec)} target="_blank" rel="noreferrer" className="mt-1 block text-xs text-slate-300 hover:text-white">
            <span className="tabular-nums text-teal-400">{mmss(c.ts_sec)}</span> {c.quote}{" "}
            <span className="text-slate-500">
              ({human(c.claim_type)}
              {c.is_risky ? ", risky" : ""}
              {c.has_source ? ", sourced" : ""})
            </span>
          </a>
        ))}
      </div>
    </article>
  );
}

/** Query-string param for static-export detail pages (/video/?id=...). */
export function useParam(name: string): string | null {
  const [v, setV] = useState<string | null>(null);
  useEffect(() => setV(new URLSearchParams(window.location.search).get(name)), [name]);
  return v;
}

export type Cited = { text: string; video_ids: string[] };

/** A statement with its evidence video links (every generated statement cites >= 1 video). */
export function CitedLine({ c }: { c: Cited }) {
  return (
    <span>
      {c.text}{" "}
      {c.video_ids.map((id, i) => (
        <Link key={id} href={`/video/?id=${id}`} className="text-xs text-teal-400 hover:underline">
          [{i + 1}]
        </Link>
      ))}
    </span>
  );
}

export const STATUS_STYLE: Record<string, string> = {
  PASS: "bg-teal-900/70 text-teal-200",
  WARN: "bg-amber-900/60 text-amber-200",
  BLOCK: "bg-red-900/70 text-red-200",
  approved: "bg-teal-600 text-white",
  rejected: "bg-navy-800 text-slate-400",
  draft: "bg-navy-800 text-slate-200",
};
