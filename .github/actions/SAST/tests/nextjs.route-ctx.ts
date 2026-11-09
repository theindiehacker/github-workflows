import type { NextRequest } from "next/server";

export async function GET(_: NextRequest, ctx: { params: Promise<{ id: string }> }) {
  const { id } = await ctx.params;
  // ruleid: nextjs-ssrf
  await fetch(id);
  return new Response("ok");
}
