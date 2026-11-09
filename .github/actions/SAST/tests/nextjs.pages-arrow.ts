import type { NextApiRequest, NextApiResponse } from "next";

const handler = (req: NextApiRequest, res: NextApiResponse) => {
  // ruleid: nextjs-ssrf
  fetch(String(req.query.u));
  res.end();
};

export default handler;
