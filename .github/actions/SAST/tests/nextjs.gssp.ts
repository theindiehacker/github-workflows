export async function getServerSideProps(ctx: { query: { u: string } }) {
  // ruleid: nextjs-ssrf
  await fetch(ctx.query.u);
  // ruleid: nextjs-open-redirect
  if (!ctx.query.a) return { redirect: { destination: ctx.query.u, permanent: false } };
  // ok: nextjs-open-redirect
  if (!ctx.query.b) return { redirect: { destination: "/login", permanent: false } };
  return { props: {} };
}
