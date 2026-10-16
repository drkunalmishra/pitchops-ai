"use client";

import Link from "next/link";
import { useEffect, useState } from "react";
import { Card, Page, Pill, STATUS_STYLE, Status, fmt, human, useParam } from "@/components/ui";
import { apiGet, apiPost } from "@/lib/api";
import { useUser } from "@/lib/useUser";

type Line = { text: string; fact_ids: string[]; pattern_ids: string[]; visual_suggestion?: string };
type Finding = { rule_id: string; severity: string; line: string; text: string; why: string; remediation: string; explanation?: string; suggested_rewrite?: string };
type Fact = { fact_id: string; field: string; value: string; source_type: string; source_url: string | null; note: string | null; video_ids: string[] | null };
type Script = {
  script_id: string;
  property_id: string;
  property_name: string;
  buyer_persona: string;
  persona_link_id: string | null;
  seller_framework: string;
  format: string;
  avatar_id: string;
  status: string;
  compliance_status: string;
  version: number;
  tool_trace: string[];
  demo_case?: boolean;
  current: {
    title: string;
    angle: string;
    hook: string;
    avatar_intro_line: string;
    narration: Line[];
    avatar_outro_line: string;
    cta: string;
    on_screen_facts: { text: string; fact_ids: string[] }[];
    missing_facts: string[];
    duration_est: number;
    similarity_to_sources: number;
    content_hash: string;
    compliance: { status: string; findings: Finding[]; policy_version: string };
  };
  versions: { version: number; by: string; at: string; note?: string }[];
  facts: Record<string, Fact>;
  approval: { version: number; script_hash: string; fact_set_version: string; persona_db_version: string; policy_version: string; reviewer_uid: string; approved_at: string } | null;
};

const SEV: Record<string, string> = { BLOCK: "border-red-800 bg-red-950/40", WARN: "border-amber-800 bg-amber-950/30", INFO: "border-navy-700 bg-navy-950/40" };

function FactChip({ id, facts }: { id: string; facts: Record<string, Fact> }) {
  const f = facts[id];
  const label = f ? `${human(f.field)}: ${f.value}` : `${id} (missing)`;
  const tip = f ? `${f.source_type}${f.note ? ` — ${f.note}` : ""}${f.source_url ? ` — ${f.source_url}` : ""}` : "unknown fact";
  const href = f?.source_url || (f?.video_ids?.length ? `/video/?id=${f.video_ids[0]}` : undefined);
  const cls = `rounded-full px-2 py-0.5 text-[11px] ${f ? (f.source_type === "official" ? "bg-teal-900/70 text-teal-200" : "bg-navy-800 text-slate-300") : "bg-red-900/70 text-red-200"}`;
  return href ? (
    <a href={href} target={f?.source_url ? "_blank" : undefined} rel="noreferrer" title={tip} className={cls}>{label}</a>
  ) : (
    <span title={tip} className={cls}>{label}</span>
  );
}

export default function ScriptPage() {
  const user = useUser();
  const id = useParam("id");
  const [s, setS] = useState<Script | null>(null);
  const [err, setErr] = useState<string | null>(null);
  const [busy, setBusy] = useState<string | null>(null);
  const [draft, setDraft] = useState<Script["current"] | null>(null);
  const [note, setNote] = useState("");

  const load = () => id && apiGet<Script>(`/v1/scripts/${id}`).then((x) => { setS(x); setDraft(null); }).catch((e) => setErr(String(e.message || e)));
  useEffect(() => { if (user && id) load(); }, [user, id]); // eslint-disable-line react-hooks/exhaustive-deps

  const act = async (label: string, fn: () => Promise<unknown>) => {
    setBusy(label);
    setErr(null);
    try { await fn(); await load(); } catch (e: any) { setErr(String(e.message || e)); } finally { setBusy(null); }
  };
  const cur = draft || s?.current;
  const editing = !!draft;
  const setLine = (i: number, text: string) => draft && setDraft({ ...draft, narration: draft.narration.map((l, j) => (j === i ? { ...l, text } : l)) });
  const btn = "rounded-lg px-3 py-1.5 text-sm disabled:opacity-50";

  return (
    <Page title={s?.current.title || "Script"} sub={s && <>{s.property_name} · {human(s.buyer_persona)} · {s.format} · {s.avatar_id} · v{s.version}</>}>
      <Status error={err} loading={!s && !err} />
      {s && cur && (
        <div className="grid gap-6 lg:grid-cols-3">
          <div className="space-y-6 lg:col-span-2">
            <Card>
              <div className="flex flex-wrap items-center gap-2">
                <span className={`rounded px-2 py-0.5 text-xs ${STATUS_STYLE[s.status]}`}>{s.status}</span>
                <span className={`rounded px-2 py-0.5 text-xs ${STATUS_STYLE[cur.compliance.status]}`}>compliance {cur.compliance.status}</span>
                <span className="text-xs text-slate-400">
                  ≈ {fmt(cur.duration_est)} s · similarity {fmt(cur.similarity_to_sources, 2)} · hash {cur.content_hash}
                </span>
              </div>
              <p className="mt-2 text-sm text-slate-300">{cur.angle}</p>
              <dl className="mt-4 space-y-3 text-sm">
                {(["hook", "avatar_intro_line"] as const).map((k) => (
                  <div key={k}>
                    <dt className="text-xs uppercase tracking-wider text-slate-400">{k === "hook" ? "Hook (≤ 3 s)" : "Presenter intro (on camera)"}</dt>
                    {editing ? (
                      <input aria-label={k} className="mt-1 w-full rounded border border-navy-700 bg-navy-950 p-2 text-white" value={draft![k]} onChange={(e) => setDraft({ ...draft!, [k]: e.target.value })} />
                    ) : (
                      <dd className="text-white">{cur[k]}</dd>
                    )}
                  </div>
                ))}
              </dl>
            </Card>
            <Card title="Narration">
              <ol className="space-y-4">
                {cur.narration.map((l, i) => (
                  <li key={i} className="text-sm">
                    {editing ? (
                      <textarea aria-label={`Line ${i + 1}`} rows={2} className="w-full rounded border border-navy-700 bg-navy-950 p-2 text-white" value={l.text} onChange={(e) => setLine(i, e.target.value)} />
                    ) : (
                      <p className="text-slate-100">{l.text}</p>
                    )}
                    <div className="mt-1 flex flex-wrap gap-1">
                      {l.fact_ids.map((f) => <FactChip key={f} id={f} facts={s.facts} />)}
                      {l.pattern_ids.map((p) => <Pill key={p}>pattern: {human(p)}</Pill>)}
                      {!l.fact_ids.length && !l.pattern_ids.length && <span className="text-[11px] text-slate-500">no citations (non-factual line)</span>}
                    </div>
                    {l.visual_suggestion && <div className="mt-1 text-xs text-slate-400">Visual: {l.visual_suggestion}</div>}
                    {editing && (
                      <button
                        disabled={!!busy}
                        className="mt-1 text-xs text-teal-400 hover:underline"
                        onClick={() =>
                          act("regen", async () => {
                            const r = await apiPost<{ text: string }>(`/v1/scripts/${s.script_id}/regenerate-line`, { index: i });
                            setLine(i, r.text);
                          }).then(() => undefined)
                        }
                      >
                        Regenerate line
                      </button>
                    )}
                  </li>
                ))}
              </ol>
            </Card>
            <Card title="Presenter outro + CTA">
              {(["avatar_outro_line", "cta"] as const).map((k) =>
                editing ? (
                  <input key={k} aria-label={k} className="mb-2 w-full rounded border border-navy-700 bg-navy-950 p-2 text-sm text-white" value={draft![k]} onChange={(e) => setDraft({ ...draft!, [k]: e.target.value })} />
                ) : (
                  <p key={k} className="mb-1 text-sm text-white">{cur[k]}</p>
                ),
              )}
              {cur.on_screen_facts.length > 0 && (
                <div className="mt-3 flex flex-wrap gap-1 text-xs">
                  <span className="text-slate-400">On-screen:</span>
                  {cur.on_screen_facts.map((f, i) => <Pill key={i}>{f.text}</Pill>)}
                </div>
              )}
              {cur.missing_facts.length > 0 && <p className="mt-2 text-xs text-slate-400">Missing facts (left out): {cur.missing_facts.join("; ")}</p>}
            </Card>
          </div>

          <div className="space-y-6">
            <Card title="Actions">
              <div className="flex flex-wrap gap-2">
                {!editing ? (
                  <button disabled={s.status === "approved" || !!busy} className={`${btn} border border-navy-700 text-slate-200`} onClick={() => setDraft(JSON.parse(JSON.stringify(s.current)))}>
                    Edit
                  </button>
                ) : (
                  <>
                    <button disabled={!!busy} className={`${btn} bg-teal-600 text-white`} onClick={() => act("save", () => apiPost(`/v1/scripts/${s.script_id}/versions`, { current: draft, note }))}>
                      Save new version
                    </button>
                    <button className={`${btn} border border-navy-700 text-slate-300`} onClick={() => setDraft(null)}>Cancel</button>
                  </>
                )}
                <button disabled={!!busy || editing} className={`${btn} border border-navy-700 text-slate-200`} onClick={() => act("compliance", () => apiPost(`/v1/scripts/${s.script_id}/compliance`, {}))}>
                  {busy === "compliance" ? "Checking…" : "Run compliance"}
                </button>
              </div>
              <label htmlFor="note" className="mt-3 block text-xs text-slate-400">Reviewer note</label>
              <input id="note" className="mt-1 w-full rounded border border-navy-700 bg-navy-950 p-2 text-sm text-white" value={note} onChange={(e) => setNote(e.target.value)} />
              <div className="mt-3 flex gap-2">
                <button
                  disabled={!!busy || editing || cur.compliance.status === "BLOCK" || s.status === "approved"}
                  title={cur.compliance.status === "BLOCK" ? "Resolve BLOCK findings first" : ""}
                  className={`${btn} bg-teal-500 font-medium text-navy-950`}
                  onClick={() => act("approve", () => apiPost(`/v1/scripts/${s.script_id}/approve`, { note }))}
                >
                  Approve
                </button>
                <button disabled={!!busy || editing} className={`${btn} border border-red-800 text-red-200`} onClick={() => act("reject", () => apiPost(`/v1/scripts/${s.script_id}/reject`, { note }))}>
                  Reject
                </button>
              </div>
              {busy && <p className="mt-2 text-xs text-slate-400">Working…</p>}
            </Card>

            <Card title={`Compliance — ${cur.compliance.status} (${cur.compliance.policy_version})`}>
              {cur.compliance.findings.length === 0 && <p className="text-sm text-slate-300">No findings.</p>}
              <ul className="space-y-2">
                {cur.compliance.findings.map((f, i) => (
                  <li key={i} className={`rounded-lg border p-2 text-xs ${SEV[f.severity] || SEV.INFO}`}>
                    <div className="font-semibold text-white">{f.severity} · {f.rule_id} · {f.line}</div>
                    {f.text && <div className="mt-0.5 italic text-slate-300">“{f.text}”</div>}
                    <div className="mt-0.5 text-slate-300">{f.why}</div>
                    <div className="mt-0.5 text-slate-400">Fix: {f.remediation}</div>
                    {f.explanation && <div className="mt-1 text-slate-300">{f.explanation}</div>}
                    {f.suggested_rewrite && <div className="mt-1 text-teal-300">Suggested: “{f.suggested_rewrite}”</div>}
                  </li>
                ))}
              </ul>
              <p className="mt-2 text-[11px] text-slate-500">Gemini explains and suggests rewrites; it never lowers a rule&apos;s severity. Not legal advice.</p>
            </Card>

            {s.approval && (
              <Card title="Approval record (frozen)">
                <dl className="space-y-1 text-xs text-slate-300">
                  {Object.entries(s.approval).map(([k, v]) => (
                    <div key={k} className="flex justify-between gap-2"><dt className="text-slate-400">{human(k)}</dt><dd className="truncate">{String(v ?? "—")}</dd></div>
                  ))}
                </dl>
              </Card>
            )}

            <Card title="Grounding">
              <p className="text-xs text-slate-300">
                Persona link: {s.persona_link_id ? <span className="text-slate-200">{s.persona_link_id}</span> : "—"}
              </p>
              <p className="mt-1 text-xs text-slate-300">Agent tool calls ({s.tool_trace.length}/8): {s.tool_trace.join(" → ")}</p>
              <p className="mt-1 text-xs text-slate-300">
                Property: <Link className="text-teal-400 hover:underline" href={`/property/?id=${s.property_id}`}>{s.property_name}</Link> · {Object.keys(s.facts).length} fact records
              </p>
            </Card>
            <Card title="Versions">
              <ul className="space-y-1 text-xs text-slate-300">
                {s.versions.map((v) => <li key={v.version}>v{v.version} · {v.by === "agent" ? "agent" : "reviewer"} · {new Date(v.at).toLocaleString()}{v.note ? ` · ${v.note}` : ""}</li>)}
              </ul>
            </Card>
          </div>
        </div>
      )}
    </Page>
  );
}
