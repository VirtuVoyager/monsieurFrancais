import { ModuleCheckPage } from "@/components/pages/module-check";

export default async function Page(props: PageProps<"/modules/[id]/check">) {
  const { id } = await props.params;
  return <ModuleCheckPage moduleId={id} />;
}
