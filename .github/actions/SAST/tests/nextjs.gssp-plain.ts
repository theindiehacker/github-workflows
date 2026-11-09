const load = async (ctx: { query: { u: string } }) => {
  // ruleid: nextjs-ssrf
  await fetch(ctx.query.u);
  return { props: {} };
};

export const getServerSideProps = load;
