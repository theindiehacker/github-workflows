import type { NextRequest } from "next/server";
import { withAuth } from "./auth";

export const GET = withAuth(async (req: NextRequest) => {
  // ruleid: nextjs-ssrf
  await fetch(req.nextUrl.searchParams.get("u")!);
  return new Response("ok");
});

export const POST = withAuth((req: NextRequest) => {
  // ruleid: nextjs-ssrf
  fetch(req.nextUrl.searchParams.get("u")!);
  return new Response("ok");
});

export const PUT = withAuth(async function (req: NextRequest) {
  // ruleid: nextjs-ssrf
  await fetch(req.nextUrl.searchParams.get("u")!);
  return new Response("ok");
});

export const config = withConfig((value: string) => {
  // ok: nextjs-ssrf
  return fetch(value);
});
