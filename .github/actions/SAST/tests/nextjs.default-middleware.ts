import type { NextRequest } from "next/server";

export default async function middleware(request: NextRequest) {
  // ruleid: nextjs-ssrf
  await fetch(request.nextUrl.searchParams.get("u")!);
}
