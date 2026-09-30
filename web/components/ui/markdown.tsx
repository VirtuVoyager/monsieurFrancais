import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";

import { fr } from "@/lib/french";

export function FrenchMarkdown({ children }: { children: string }) {
  return (
    <div
      lang="fr"
      className="space-y-4 leading-relaxed [&_em]:text-accent [&_h2]:mt-8 [&_h2]:font-serif [&_h2]:text-lg [&_h2]:font-semibold [&_li]:ml-5 [&_li]:list-disc [&_strong]:font-semibold [&_table]:w-full [&_table]:text-sm [&_td]:border-b [&_td]:border-line [&_td]:px-3 [&_td]:py-2 [&_th]:border-b [&_th]:border-line [&_th]:px-3 [&_th]:py-2 [&_th]:text-left [&_th]:font-semibold"
    >
      <ReactMarkdown remarkPlugins={[remarkGfm]}>{fr(children)}</ReactMarkdown>
    </div>
  );
}
