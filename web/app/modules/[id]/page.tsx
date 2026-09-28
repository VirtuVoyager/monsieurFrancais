import { ModulePage } from "@/components/pages/module";

export default async function Page(props: PageProps<"/modules/[id]">) {
  const { id } = await props.params;
  return <ModulePage id={id} />;
}
