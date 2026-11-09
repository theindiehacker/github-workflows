import type { NextApiRequest, NextApiResponse } from "next";
import { withAuth } from "./auth";

const handler = (req: NextApiRequest, res: NextApiResponse) => {
  // ruleid: nextjs-ssrf
  fetch(String(req.query.u));
  res.end();
};

export default withAuth(handler);
