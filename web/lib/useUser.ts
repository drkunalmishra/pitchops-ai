"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { onAuthStateChanged, type User } from "firebase/auth";
import { auth } from "@/lib/firebase";

export function useUser(): User | null {
  const router = useRouter();
  const [user, setUser] = useState<User | null>(null);
  useEffect(
    () =>
      onAuthStateChanged(auth, (u) => {
        if (!u) router.replace("/");
        else setUser(u);
      }),
    [router],
  );
  return user;
}
