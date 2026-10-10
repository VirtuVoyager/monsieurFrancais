import { RepeatPlayerPage } from "@/components/pages/repeat";

export default async function Page(props: PageProps<"/speak/repeat/[id]">) {
  const { id } = await props.params;
  return <RepeatPlayerPage id={id} />;
}
