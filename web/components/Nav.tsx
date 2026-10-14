"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { signOut, type User } from "firebase/auth";
import { auth } from "@/lib/firebase";

const LINKS = [
  { href: "/dashboard/", label: "Dashboard" },
  { href: "/review/", label: "Review queue" },
];

export default function Nav({ user }: { user: User }) {
  const path = usePathname();
  return (
    <header className="mb-8 flex flex-wrap items-center justify-between gap-4">
      <div className="flex items-center gap-6">
        <div className="text-sm font-semibold tracking-widest text-teal-400">PITCHOPS AI</div>
        <nav className="flex gap-1 text-sm">
          {LINKS.map((l) => (
            <Link
              key={l.href}
              href={l.href}
              className={`rounded-lg px-3 py-1.5 ${path === l.href ? "bg-navy-800 text-white" : "text-slate-400 hover:text-white"}`}
            >
              {l.label}
            </Link>
          ))}
        </nav>
      </div>
      <div className="flex items-center gap-3 text-sm text-slate-400">
        <span className="max-w-48 truncate">{user.email}</span>
        <button
          onClick={() => signOut(auth)}
          className="rounded-lg border border-navy-700 px-3 py-1.5 hover:border-teal-500 hover:text-white"
        >
          Sign out
        </button>
      </div>
    </header>
  );
}
