import type { NextRequest } from "next/server";
import { withAuth, withLog } from "./auth";

const items = [{ url: "https://api.example.com/x" }];

export const GET = withLog(withAuth(async (req: NextRequest) => {
  // ruleid: nextjs-ssrf
  await fetch(req.nextUrl.searchParams.get("u")!);
  // handler の中のコールバックの引数は、リクエストの値として扱わない
  await Promise.all(items.map(async (item) => fetch(item.url)));
  return new Response("ok");
}));

export const POST = withLog(withAuth((req: NextRequest) => {
  // ruleid: nextjs-ssrf
  fetch(req.nextUrl.searchParams.get("u")!);
  items.forEach((item) => fetch(item.url));
  return new Response("ok");
}));
