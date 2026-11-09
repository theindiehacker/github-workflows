import type { NextApiRequest, NextApiResponse } from "next";

async function handler(req: NextApiRequest, res: NextApiResponse) {
  // ruleid: nextjs-ssrf
  await fetch(String(req.query.u));
  res.end();
}

export default handler;
