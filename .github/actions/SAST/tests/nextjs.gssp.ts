export async function getServerSideProps(ctx: { query: { u: string } }) {
  // ruleid: nextjs-ssrf
  await fetch(ctx.query.u);
  return { props: {} };
}
