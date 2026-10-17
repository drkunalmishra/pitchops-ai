"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import {
  GoogleAuthProvider,
  onAuthStateChanged,
  signInAnonymously,
  signInWithEmailAndPassword,
  signInWithPopup,
} from "firebase/auth";
import { auth } from "@/lib/firebase";

export default function LoginPage() {
  const router = useRouter();
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  useEffect(() => onAuthStateChanged(auth, (u) => u && router.replace("/dashboard/")), [router]);

  async function run(fn: () => Promise<unknown>) {
    setBusy(true);
    setError(null);
    try {
      await fn();
    } catch (e) {
      setError(e instanceof Error ? e.message.replace("Firebase: ", "") : "Sign-in failed");
    } finally {
      setBusy(false);
    }
  }

  return (
    <main className="flex min-h-screen items-center justify-center px-4">
      <div className="w-full max-w-sm rounded-2xl border border-navy-700 bg-navy-900 p-8 shadow-2xl">
        <div className="mb-8">
          <div className="text-sm font-semibold tracking-widest text-teal-400">PITCHOPS AI</div>
          <h1 className="mt-2 text-2xl font-semibold">Sign in</h1>
          <p className="mt-1 text-sm text-slate-400">Sales-content intelligence for Dubai real estate.</p>
        </div>
        <form
          className="space-y-4"
          onSubmit={(e) => {
            e.preventDefault();
            run(() => signInWithEmailAndPassword(auth, email, password));
          }}
        >
          <input
            type="email" required placeholder="Email" value={email} autoComplete="username"
            onChange={(e) => setEmail(e.target.value)}
            className="w-full rounded-lg border border-navy-700 bg-navy-950 px-3 py-2.5 text-sm outline-none focus:border-teal-500"
          />
          <input
            type="password" required placeholder="Password" value={password} autoComplete="current-password"
            onChange={(e) => setPassword(e.target.value)}
            className="w-full rounded-lg border border-navy-700 bg-navy-950 px-3 py-2.5 text-sm outline-none focus:border-teal-500"
          />
          <button
            type="submit" disabled={busy}
            className="w-full rounded-lg bg-teal-500 py-2.5 text-sm font-semibold text-navy-950 hover:bg-teal-400 disabled:opacity-60"
          >
            {busy ? "Signing in…" : "Sign in"}
          </button>
        </form>
        <button
          onClick={() => run(() => signInAnonymously(auth))} disabled={busy}
          className="mt-5 w-full rounded-lg border border-teal-500/60 bg-teal-500/10 py-2.5 text-sm font-semibold text-teal-300 hover:bg-teal-500/20 disabled:opacity-60"
        >
          Judge access (one click, no password)
        </button>
        <p className="mt-2 text-center text-xs text-slate-500">
          For AI Builder Cup evaluators. Opens the full prototype as a guest; actions are audit-logged.
        </p>
        <div className="my-5 flex items-center gap-3 text-xs text-slate-500">
          <div className="h-px flex-1 bg-navy-700" /> or <div className="h-px flex-1 bg-navy-700" />
        </div>
        <button
          onClick={() => run(() => signInWithPopup(auth, new GoogleAuthProvider()))} disabled={busy}
          className="w-full rounded-lg border border-navy-700 py-2.5 text-sm font-medium hover:border-teal-500"
        >
          Continue with Google
        </button>
        {error && <p className="mt-4 text-sm text-red-400">{error}</p>}
      </div>
    </main>
  );
}
