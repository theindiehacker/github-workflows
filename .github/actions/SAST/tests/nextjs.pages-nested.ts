import type { NextApiRequest, NextApiResponse } from "next";
import { withAuth, withLog } from "./auth";

export default withLog(withAuth(async (req: NextApiRequest, res: NextApiResponse) => {
  // ruleid: nextjs-ssrf
  await fetch(String(req.query.u));
  res.end();
}));
