export default async function Page(props: { searchParams: Promise<{ u: string }>; params: Promise<{ id: string }> }) {
  const sp = await props.searchParams;
  const { id } = await props.params;
  // ruleid: nextjs-ssrf
  await fetch(sp.u);
  // ruleid: nextjs-ssrf
  await fetch(id);
  return null;
}
