import { auth } from "@/lib/firebase";

async function authed(path: string, init?: RequestInit): Promise<Response> {
  const user = auth.currentUser;
  if (!user) throw new Error("not signed in");
  const token = await user.getIdToken();
  const res = await fetch(`/api${path}`, {
    ...init,
    headers: { ...(init?.headers || {}), Authorization: `Bearer ${token}` },
  });
  if (!res.ok) {
    let detail = "";
    try {
      const j = await res.json();
      detail = typeof j.detail === "string" ? j.detail : JSON.stringify(j.detail ?? j);
    } catch {
      /* not JSON */
    }
    throw new Error(`${res.status} ${detail || res.statusText}`);
  }
  return res;
}

async function call<T>(path: string, init?: RequestInit): Promise<T> {
  const res = await authed(path, { ...init, headers: { ...(init?.headers || {}), "Content-Type": "application/json" } });
  return (await res.json()) as T;
}

export const apiGet = <T,>(path: string) => call<T>(path);
export const apiPost = <T,>(path: string, body: unknown) => call<T>(path, { method: "POST", body: JSON.stringify(body) });
/** Authenticated binary download (images / videos) -> object URL for <img> / <video>. */
export const apiBlobUrl = async (path: string) => URL.createObjectURL(await (await authed(path)).blob());
export const apiUpload = async <T,>(path: string, file: File) => {
  const fd = new FormData();
  fd.append("file", file);
  return (await (await authed(path, { method: "POST", body: fd })).json()) as T;
};
