async function Page({ searchParams }: { searchParams: Promise<{ u: string }> }) {
  const { u } = await searchParams;
  // ruleid: nextjs-ssrf
  await fetch(u);
  return null;
}

export default Page;
