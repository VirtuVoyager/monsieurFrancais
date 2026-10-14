import { LessonPage } from "@/components/pages/lesson";

export default async function Page(props: PageProps<"/lessons/[...id]">) {
  const { id } = await props.params;
  return <LessonPage id={id.map(decodeURIComponent).join("/")} />;
}
