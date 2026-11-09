import { withSession } from "./session";

async function load(ctx: { query: { u: string } }) {
  // ruleid: nextjs-ssrf
  await fetch(ctx.query.u);
  return { props: {} };
}

export const getServerSideProps = withSession(load);
