import { getApp, getApps, initializeApp, type FirebaseOptions } from "firebase/app";
import { getAuth } from "firebase/auth";

const config: FirebaseOptions = JSON.parse(process.env.NEXT_PUBLIC_FIREBASE_CONFIG || "{}");

export const app = getApps().length ? getApp() : initializeApp(config);
export const auth = getAuth(app);

export async function apiGet<T>(path: string): Promise<T> {
  const user = auth.currentUser;
  if (!user) throw new Error("not signed in");
  const token = await user.getIdToken();
  const res = await fetch(`/api${path}`, { headers: { Authorization: `Bearer ${token}` } });
  if (!res.ok) throw new Error(`${res.status} ${res.statusText}`);
  return (await res.json()) as T;
}
