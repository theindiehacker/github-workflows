import type { NextApiRequest, NextApiResponse } from "next";
import { db } from "./db";

export default async function handler(req: NextApiRequest, res: NextApiResponse) {
  // ruleid: nextjs-ssrf
  await fetch(String(req.query.u));
  // ruleid: nextjs-ssrf
  await fetch(req.body.u);
  // ruleid: nextjs-sql-injection
  await db.query(`SELECT * FROM t WHERE a = '${req.query.a}'`);
  // ruleid: nextjs-open-redirect
  res.redirect(String(req.query.next));
  // ruleid: nextjs-open-redirect
  res.redirect(302, String(req.query.next));
  // ok: nextjs-open-redirect
  res.redirect("/login");
}
