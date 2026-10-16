"use client";

import { Card, Page, Status, useApi } from "@/components/ui";

type Avatar = {
  avatar_id: string;
  name: string;
  heritage: string;
  languages: string;
  presentation: string;
  voice: string;
  status: string | null;
  candidates: { id: string }[] | null;
  approved_candidate: string | null;
};

export default function AvatarsPage() {
  const { data, error } = useApi<Avatar[]>("/v1/media/avatars");
  return (
    <Page title="Avatars" sub="8 fictional bilingual presenters (D17). Portraits are generated only after you approve the Imagen step; none resemble real people.">
      <Status error={error} loading={!data} />
      {data && (
        <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
          {data.map((a) => (
            <Card key={a.avatar_id}>
              <div className="flex h-32 items-center justify-center rounded-lg bg-navy-800 text-3xl font-semibold text-teal-400" aria-hidden>
                {a.name[0]}
              </div>
              <h2 className="mt-3 font-medium text-white">{a.name}</h2>
              <p className="text-xs text-slate-300">{a.heritage} · {a.languages}</p>
              <p className="mt-1 text-xs text-slate-400">Narration voice: {a.voice}</p>
              <p className="mt-2 text-xs text-amber-300">{a.approved_candidate ? "Portrait approved" : a.status || "Portrait not generated yet"}</p>
            </Card>
          ))}
        </div>
      )}
    </Page>
  );
}
