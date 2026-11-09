import type { NextRequest } from "next/server";

async function handler(req: NextRequest) {
  // ruleid: nextjs-ssrf
  await fetch(req.nextUrl.searchParams.get("u")!);
  return new Response("ok");
}

async function other(value: string) {
  // ok: nextjs-ssrf
  return fetch(value);
}

export { handler as GET, other };
