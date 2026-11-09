import type { NextApiRequest, NextApiResponse } from "next";
import { withAuth } from "./auth";

export default withAuth(async (req: NextApiRequest, res: NextApiResponse) => {
  // ruleid: nextjs-ssrf
  await fetch(String(req.query.u));
  res.end();
});
