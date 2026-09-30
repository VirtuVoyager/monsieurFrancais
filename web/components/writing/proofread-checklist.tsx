"use client";

import { useErrorFingerprint } from "@/lib/queries";

/** Before submitting, check the text against your own most frequent mistakes. */
export function ProofreadChecklist() {
  const errors = useErrorFingerprint();
  if (!errors.data?.length) return null;
  return (
    <div className="rounded-xl border border-line p-3">
      <p className="mb-2 text-sm font-medium">Proofread for your usual errors</p>
      <ul className="space-y-1 text-sm">
        {errors.data.map((e) => (
          <li key={e.tag} className="flex items-start gap-2">
            <input type="checkbox" className="mt-1" aria-label={e.tag} />
            <span>
              <span className="font-medium">{e.tag}</span>{" "}
              <span className="text-muted">
                ({e.count}×) e.g. <span lang="fr">{e.example}</span> →{" "}
                <span lang="fr">{e.correction}</span>
              </span>
            </span>
          </li>
        ))}
      </ul>
    </div>
  );
}
