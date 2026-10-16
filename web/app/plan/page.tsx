"use client";

import Link from "next/link";
import { useEffect, useState } from "react";
import { Card, Page, Status, Tile, fmt, human, usd, useParam } from "@/components/ui";
import { apiBlobUrl, apiGet, apiPost } from "@/lib/api";
import { useUser } from "@/lib/useUser";

type Shot = { kind: string; veo: boolean; audio: boolean; sec: number; text?: string; prompt_key?: string; image_id?: string | null };
type Plan = {
  plan_id: string;
  property_id: string;
  property_name: string;
  area: string;
  format: string;
  script_id: string;
  script_version: number;
  avatar_id: string;
  state: string;
  shots: Shot[];
  est_cost_usd: number;
  est_duration_sec: number;
  max_sec: number;
  preview_gcs?: string;
  final_gcs?: string;
  preview_qc?: string[];
  preview_duration_sec?: number;
  approval?: { approver_uid: string; approved_at: string; plan_hash: string; est_cost_usd: number };
  actual_cost_usd?: number;
};
const AVATARS = ["avatar_in", "avatar_me", "avatar_na", "avatar_ea", "avatar_af", "avatar_ru", "avatar_eu", "avatar_sa"];

export default function PlanPage() {
  const user = useUser();
  const id = useParam("id");
  const [p, setP] = useState<Plan | null>(null);
  const [err, setErr] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);
  const [videoUrl, setVideoUrl] = useState<string | null>(null);
  const [note, setNote] = useState("");

  const load = () => id && apiGet<Plan>(`/v1/media/plans/${id}`).then(setP).catch((e) => setErr(String(e.message)));
  useEffect(() => { if (user && id) load(); }, [user, id]); // eslint-disable-line react-hooks/exhaustive-deps
  useEffect(() => {
    if (!p) return;
    const kind = p.final_gcs ? "final" : p.preview_gcs ? "preview" : null;
    if (kind) apiBlobUrl(`/v1/media/plans/${p.plan_id}/video/${kind}`).then(setVideoUrl).catch(() => setVideoUrl(null));
  }, [p?.preview_gcs, p?.final_gcs]); // eslint-disable-line react-hooks/exhaustive-deps

  const act = async (fn: () => Promise<unknown>) => {
    setBusy(true);
    setErr(null);
    try { await fn(); await load(); } catch (e: any) { setErr(String(e.message || e)); } finally { setBusy(false); }
  };
  const canApprove = p && ["PREVIEW_READY", "AWAITING_APPROVAL"].includes(p.state);
  return (
    <Page title={p?.property_name || "Video plan"} sub={p && <>{p.format === "16x9" ? "16:9 walkthrough ≤ 120 s" : "9:16 Short ≤ 55 s"} · {p.area} · state {p.state}</>}>
      <Status error={err} loading={!p && !err} />
      {p && (
        <div className="grid gap-6 lg:grid-cols-3">
          <div className="space-y-6 lg:col-span-2">
            <Card title={p.final_gcs ? "Final video" : "Free preview (no Veo — placeholders mark the paid shots)"}>
              {videoUrl ? (
                <video src={videoUrl} controls className={`mx-auto rounded-lg ${p.format === "9x16" ? "max-h-[70vh]" : "w-full"}`} />
              ) : (
                <p className="text-sm text-slate-400">{p.state === "DRAFT" ? "Preview not rendered yet (run the preview job)." : "Loading video…"}</p>
              )}
              {!!p.preview_qc?.length && <p className="mt-2 text-xs text-amber-300">QC: {p.preview_qc.join("; ")}</p>}
            </Card>
            <Card title="Shot list">
              <ol className="space-y-2 text-sm">
                {p.shots.map((s, i) => (
                  <li key={i} className="flex flex-wrap items-start justify-between gap-2 border-b border-navy-800 pb-2">
                    <div className="min-w-0 flex-1">
                      <span className="font-medium text-white">{i + 1}. {human(s.kind)}</span>
                      {s.prompt_key && <span className="ml-2 text-xs text-slate-400">{human(s.prompt_key)}</span>}
                      {s.text && <p className="mt-0.5 text-slate-300">{s.text}</p>}
                    </div>
                    <div className="flex items-center gap-2 text-xs">
                      <span className="tabular-nums text-slate-400">{fmt(s.sec)} s</span>
                      {s.veo ? <span className="rounded bg-amber-900/60 px-2 py-0.5 text-amber-200">Veo{s.audio ? " + voice" : ""}</span> : <span className="rounded bg-navy-800 px-2 py-0.5 text-slate-300">free</span>}
                      {s.kind === "hero_clip" && ["DRAFT", "PREVIEW_READY", "AWAITING_APPROVAL"].includes(p.state) && (
                        <button disabled={busy} className="text-teal-400 hover:underline" onClick={() => act(() => apiPost(`/v1/media/plans/${p.plan_id}/edit`, { drop_hero: i }))}>
                          remove
                        </button>
                      )}
                    </div>
                  </li>
                ))}
              </ol>
            </Card>
          </div>
          <div className="space-y-6">
            <div className="grid grid-cols-2 gap-3">
              <Tile label="Veo estimate" value={usd(p.est_cost_usd)} sub={p.actual_cost_usd !== undefined ? `actual ${usd(p.actual_cost_usd)}` : undefined} />
              <Tile label="Length" value={`${fmt(p.preview_duration_sec ?? p.est_duration_sec)} s`} sub={`max ${p.max_sec} s`} />
            </div>
            <Card title="Presenter">
              <label htmlFor="av" className="text-xs text-slate-400">Avatar (fictional presenter)</label>
              <select id="av" disabled={busy || !["DRAFT", "PREVIEW_READY", "AWAITING_APPROVAL"].includes(p.state)} value={p.avatar_id}
                className="mt-1 w-full rounded border border-navy-700 bg-navy-950 p-2 text-sm text-white"
                onChange={(e) => act(() => apiPost(`/v1/media/plans/${p.plan_id}/edit`, { avatar_id: e.target.value }))}>
                {AVATARS.map((a) => <option key={a} value={a}>{a}</option>)}
              </select>
              <p className="mt-2 text-xs text-slate-400">
                Script: <Link href={`/script/?id=${p.script_id}`} className="text-teal-400 hover:underline">{p.script_id}</Link> v{p.script_version}
                {" · "}Images: <Link href={`/images/?id=${p.property_id}`} className="text-teal-400 hover:underline">edit</Link>
              </p>
              <p className="mt-1 text-xs text-slate-500">Changing the plan sends it back to DRAFT so the preview is re-rendered before approval.</p>
            </Card>
            <Card title="Approval">
              {p.approval ? (
                <dl className="space-y-1 text-xs text-slate-300">
                  {Object.entries(p.approval).map(([k, v]) => <div key={k} className="flex justify-between gap-2"><dt className="text-slate-400">{human(k)}</dt><dd className="truncate">{String(v)}</dd></div>)}
                </dl>
              ) : (
                <>
                  <label htmlFor="note" className="text-xs text-slate-400">Note</label>
                  <input id="note" value={note} onChange={(e) => setNote(e.target.value)} className="mt-1 w-full rounded border border-navy-700 bg-navy-950 p-2 text-sm text-white" />
                  <div className="mt-3 flex gap-2">
                    <button disabled={busy || !canApprove} title={canApprove ? "" : "Render the preview first"} className="rounded-lg bg-teal-500 px-3 py-1.5 text-sm font-medium text-navy-950 disabled:opacity-50"
                      onClick={() => window.confirm(`Approve Veo generation for about ${usd(p.est_cost_usd)}? This also approves the script.`) && act(() => apiPost(`/v1/media/plans/${p.plan_id}/approve`, { note }))}>
                      Approve {usd(p.est_cost_usd)}
                    </button>
                    <button disabled={busy || ["GENERATING", "COMPOSING"].includes(p.state)} className="rounded-lg border border-red-800 px-3 py-1.5 text-sm text-red-200 disabled:opacity-50"
                      onClick={() => act(() => apiPost(`/v1/media/plans/${p.plan_id}/reject`, { note }))}>
                      Reject
                    </button>
                  </div>
                  <p className="mt-2 text-xs text-slate-500">Approval is refused if it would exceed the media budget or the $200 project cap.</p>
                </>
              )}
            </Card>
          </div>
        </div>
      )}
    </Page>
  );
}
