import * as nsFs from "node:fs";
import { type NextRequest } from "next/server";

const { stat, rename } = require("node:fs/promises");
const nodeFs = require("node:fs");

export async function GET(req: NextRequest) {
  const u = req.nextUrl.searchParams.get("u")!;
  // ruleid: nextjs-path-traversal
  await stat(u);
  // ruleid: nextjs-path-traversal
  await rename("x", u);
  // ruleid: nextjs-path-traversal
  nodeFs.stat(u, () => {});
  // ruleid: nextjs-path-traversal
  nsFs.stat(u, () => {});
  // ruleid: nextjs-path-traversal
  nsFs.rename("x", u, () => {});
  // ok: nextjs-path-traversal
  other.stat(u);
  return new Response("ok");
}
