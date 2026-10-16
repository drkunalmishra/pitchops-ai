"use client";

import { useEffect, useState } from "react";
import { Card, Page, Status, human, useApi, useParam } from "@/components/ui";
import { apiBlobUrl, apiGet, apiPost, apiUpload } from "@/lib/api";

type Row = { property_id: string; canonical_name: string; media_candidate: string; images: number; selected: number };
type Img = { id: string; tag: string; quality: number; selected: boolean; origin: string; width: number; caption?: string };
const TAGS = ["aerial", "exterior_facade", "skyline_view", "interior_living", "interior_bedroom", "kitchen", "bathroom", "pool_amenity", "gym_amenity", "lobby", "community", "masterplan", "other"];

function Thumb({ pid, img, onToggle }: { pid: string; img: Img; onToggle: () => void }) {
  const [url, setUrl] = useState<string | null>(null);
  useEffect(() => { apiBlobUrl(`/v1/media/image/${pid}/${img.id}`).then(setUrl).catch(() => setUrl(null)); }, [pid, img.id]);
  return (
    <button onClick={onToggle} aria-pressed={img.selected} className={`overflow-hidden rounded-lg border-2 text-left ${img.selected ? "border-teal-400" : "border-navy-700 opacity-60"}`}>
      {url ? <img src={url} alt={img.caption || human(img.tag)} className="h-32 w-full object-cover" /> : <div className="h-32 bg-navy-800" />}
      <div className="p-1.5 text-[11px] text-slate-300">
        {human(img.tag)} · q {img.quality.toFixed(2)} · {img.width}px{img.origin === "manual_upload" ? " · uploaded" : ""}
      </div>
    </button>
  );
}

function Editor({ pid }: { pid: string }) {
  const [imgs, setImgs] = useState<Img[] | null>(null);
  const [msg, setMsg] = useState<string | null>(null);
  const [tag, setTag] = useState("exterior_facade");
  const load = () => apiGet<{ images: Img[] }>(`/v1/media/images/${pid}`).then((d) => setImgs(d.images || []));
  useEffect(() => { load(); }, [pid]); // eslint-disable-line react-hooks/exhaustive-deps
  const toggle = async (id: string) => {
    const next = (imgs || []).map((i) => (i.id === id ? { ...i, selected: !i.selected } : i));
    setImgs(next);
    await apiPost(`/v1/media/images/${pid}/selection`, { selected: next.filter((i) => i.selected).map((i) => i.id) });
  };
  const onFiles = async (files: FileList | null) => {
    if (!files) return;
    setMsg("Uploading…");
    let low = 0;
    for (const f of Array.from(files)) {
      const r = await apiUpload<{ low_res: boolean }>(`/v1/media/images/${pid}/upload?tag=${tag}`, f);
      low += r.low_res ? 1 : 0;
    }
    setMsg(`Uploaded ${files.length} image(s)${low ? ` — ${low} below 1280 px (may look soft)` : ""}.`);
    load();
  };
  return (
    <Card title={`Images (${imgs?.filter((i) => i.selected).length ?? 0} selected — aim for 8–15)`}>
      <div className="mb-3 flex flex-wrap items-center gap-2 text-sm">
        <label htmlFor="tag" className="text-slate-400">Upload as</label>
        <select id="tag" value={tag} onChange={(e) => setTag(e.target.value)} className="rounded border border-navy-700 bg-navy-950 p-1.5 text-white">
          {TAGS.map((t) => <option key={t} value={t}>{human(t)}</option>)}
        </select>
        <label className="cursor-pointer rounded-lg bg-teal-600 px-3 py-1.5 text-white">
          Upload images
          <input type="file" accept="image/*" multiple className="sr-only" onChange={(e) => onFiles(e.target.files)} />
        </label>
        <span className="text-xs text-slate-400">Use images you are allowed to use (developer press kits / brochures). Stored privately, never published.</span>
      </div>
      {msg && <p className="mb-2 text-xs text-teal-300">{msg}</p>}
      {!imgs && <p className="text-slate-400">Loading…</p>}
      {imgs && imgs.length === 0 && <p className="text-sm text-amber-300">No images yet — upload some.</p>}
      <div className="grid grid-cols-2 gap-3 sm:grid-cols-3 lg:grid-cols-5">
        {(imgs || []).map((i) => <Thumb key={i.id} pid={pid} img={i} onToggle={() => toggle(i.id)} />)}
      </div>
    </Card>
  );
}

export default function ImagesPage() {
  const { data, error } = useApi<Row[]>("/v1/media/images");
  const param = useParam("id");
  const [pid, setPid] = useState<string | null>(null);
  const cur = pid || param || data?.[0]?.property_id || null;
  return (
    <Page title="Property images" sub="Official-site images (robots.txt respected) tagged by Gemini Flash-Lite; select 8–15 per property or upload your own.">
      <Status error={error} loading={!data} />
      {data && (
        <div className="grid gap-6 lg:grid-cols-4">
          <Card title="Media properties">
            <ul className="max-h-[70vh] space-y-1 overflow-y-auto text-sm">
              {data.map((r) => (
                <li key={r.property_id}>
                  <button onClick={() => setPid(r.property_id)} className={`flex w-full justify-between rounded px-2 py-1 text-left ${cur === r.property_id ? "bg-navy-800 text-white" : "text-slate-300 hover:text-white"}`}>
                    <span className="truncate">{r.canonical_name}</span>
                    <span className={`tabular-nums ${r.selected < 4 ? "text-amber-300" : "text-slate-400"}`}>{r.selected}/{r.images}</span>
                  </button>
                </li>
              ))}
            </ul>
          </Card>
          <div className="lg:col-span-3">{cur && <Editor key={cur} pid={cur} />}</div>
        </div>
      )}
    </Page>
  );
}
