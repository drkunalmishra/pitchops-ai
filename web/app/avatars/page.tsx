"use client";

import { useEffect, useState } from "react";
import { Card, Page, Status } from "@/components/ui";
import { apiBlobUrl, apiGet, apiPost } from "@/lib/api";
import { useUser } from "@/lib/useUser";

type Avatar = {
  avatar_id: string;
  name: string;
  heritage: string;
  languages: string;
  voice: string;
  status: string | null;
  candidates: { id: string }[] | null;
  approved_candidate: string | null;
};

function Candidate({ a, id, chosen, onPick, busy }: { a: Avatar; id: string; chosen: boolean; onPick: () => void; busy: boolean }) {
  const [url, setUrl] = useState<string | null>(null);
  useEffect(() => { apiBlobUrl(`/v1/media/avatar/${a.avatar_id}/${id}`).then(setUrl).catch(() => setUrl(null)); }, [a.avatar_id, id]);
  return (
    <button disabled={busy} onClick={onPick} aria-pressed={chosen} title={chosen ? "Approved portrait" : "Use this portrait"}
      className={`overflow-hidden rounded-lg border-2 ${chosen ? "border-teal-400" : "border-navy-700 hover:border-slate-400"}`}>
      {url ? <img src={url} alt={`Candidate portrait for ${a.name} (fictional)`} className="aspect-video w-full object-cover" /> : <div className="aspect-video bg-navy-800" />}
    </button>
  );
}

export default function AvatarsPage() {
  const user = useUser();
  const [data, setData] = useState<Avatar[] | null>(null);
  const [err, setErr] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);
  const load = () => apiGet<Avatar[]>("/v1/media/avatars").then(setData).catch((e) => setErr(String(e.message)));
  useEffect(() => { if (user) load(); }, [user]); // eslint-disable-line react-hooks/exhaustive-deps
  const pick = async (a: Avatar, id: string) => {
    setBusy(true);
    try { await apiPost(`/v1/media/avatars/${a.avatar_id}/approve`, { candidate_id: id }); await load(); } catch (e: any) { setErr(String(e.message)); } finally { setBusy(false); }
  };
  const approved = data?.filter((a) => a.approved_candidate).length ?? 0;
  return (
    <Page title="Avatars" sub={`8 fictional bilingual presenters (D17). Click the portrait to use for each — it becomes the first frame of the Veo intro/outro. ${approved}/8 approved.`}>
      <Status error={err} loading={!data && !err} />
      {data && (
        <div className="grid gap-4 md:grid-cols-2">
          {data.map((a) => (
            <Card key={a.avatar_id}>
              <div className="flex items-baseline justify-between gap-2">
                <h2 className="font-medium text-white">{a.name} <span className="text-xs font-normal text-slate-400">{a.avatar_id}</span></h2>
                <span className={`text-xs ${a.approved_candidate ? "text-teal-400" : "text-amber-300"}`}>{a.approved_candidate ? "approved" : a.candidates?.length ? "pick one" : a.status || "not generated"}</span>
              </div>
              <p className="text-xs text-slate-300">{a.heritage} · {a.languages} · narration voice {a.voice}</p>
              <div className="mt-3 grid grid-cols-2 gap-2">
                {(a.candidates || []).map((c) => (
                  <Candidate key={c.id} a={a} id={c.id} chosen={a.approved_candidate === c.id} busy={busy} onPick={() => pick(a, c.id)} />
                ))}
              </div>
            </Card>
          ))}
        </div>
      )}
      <p className="mt-4 text-xs text-slate-400">Portraits are AI-generated fictional people (Gemini image model), stored privately; videos carry an AI-presenter disclosure.</p>
    </Page>
  );
}
