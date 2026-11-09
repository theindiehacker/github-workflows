import type { NextRequest } from "next/server";
import { withAuth } from "./auth";

const items = [{ url: "https://api.example.com/x" }];

export const GET = withAuth(async (req: NextRequest) => {
  // ruleid: nextjs-ssrf
  await fetch(req.nextUrl.searchParams.get("u")!);
  // ok: nextjs-ssrf
  await Promise.all(items.map(async (item) => fetch(item.url)));
  return new Response("ok");
});

export const POST = withAuth((req: NextRequest) => {
  // ruleid: nextjs-ssrf
  fetch(req.nextUrl.searchParams.get("u")!);
  return new Response("ok");
});

export const config = withConfig((value: string) => {
  // ok: nextjs-ssrf
  return fetch(value);
});
