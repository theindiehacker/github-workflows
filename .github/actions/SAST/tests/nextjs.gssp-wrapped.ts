import { withSession } from "./session";

export const getServerSideProps = withSession(async (ctx: { query: { u: string } }) => {
  // ruleid: nextjs-ssrf
  await fetch(ctx.query.u);
  return { props: {} };
});
