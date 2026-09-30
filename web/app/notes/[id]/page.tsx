import { notFound } from "next/navigation";

import { NotePage } from "@/components/pages/note";

export default async function Page(props: PageProps<"/notes/[id]">) {
  const { id } = await props.params;
  const noteId = Number(id);
  if (!Number.isInteger(noteId)) notFound();
  return <NotePage id={noteId} />;
}
