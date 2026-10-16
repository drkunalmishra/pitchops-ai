"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { useEffect, useState } from "react";
import { signOut, type User } from "firebase/auth";
import { auth } from "@/lib/firebase";
import { apiGet } from "@/lib/api";

const LINKS = [
  { href: "/dashboard/", label: "Overview" },
  { href: "/personas/", label: "Personas" },
  { href: "/properties/", label: "Properties" },
  { href: "/companies/", label: "Companies" },
  { href: "/studio/", label: "Script Studio" },
  { href: "/finops/", label: "FinOps" },
  { href: "/review/", label: "Review queue" },
];

let adminCache: boolean | null = null;

export default function Nav({ user }: { user: User }) {
  const path = usePathname();
  const [admin, setAdmin] = useState<boolean>(!!adminCache);
  useEffect(() => {
    if (adminCache !== null) return;
    apiGet<{ admin: boolean }>("/v1/me")
      .then((r) => {
        adminCache = r.admin;
        setAdmin(r.admin);
      })
      .catch(() => undefined);
  }, []);
  const links = admin ? [...LINKS, { href: "/admin/", label: "Admin / QA" }] : LINKS;
  return (
    <header className="mb-8 flex flex-wrap items-center justify-between gap-4">
      <div className="flex flex-wrap items-center gap-6">
        <Link href="/dashboard/" className="text-sm font-semibold tracking-widest text-teal-400">
          PITCHOPS AI
        </Link>
        <nav aria-label="Main" className="flex flex-wrap gap-1 text-sm">
          {links.map((l) => (
            <Link
              key={l.href}
              href={l.href}
              aria-current={path === l.href ? "page" : undefined}
              className={`rounded-lg px-3 py-1.5 ${path === l.href ? "bg-navy-800 text-white" : "text-slate-300 hover:text-white"}`}
            >
              {l.label}
            </Link>
          ))}
        </nav>
      </div>
      <div className="flex items-center gap-3 text-sm text-slate-300">
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
