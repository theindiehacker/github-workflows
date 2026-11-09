import type { NextRequest } from "next/server";
import { withAuth } from "./auth";

const arrow = async (req: NextRequest) => {
  // ruleid: nextjs-ssrf
  await fetch(req.nextUrl.searchParams.get("u")!);
  return new Response("ok");
};

async function GET(req: NextRequest) {
  // ruleid: nextjs-ssrf
  await fetch(req.nextUrl.searchParams.get("u")!);
  return new Response("ok");
}

async function wrapped(req: NextRequest) {
  // ruleid: nextjs-ssrf
  await fetch(req.nextUrl.searchParams.get("u")!);
  return new Response("ok");
}

const wrappedArrow = async (req: NextRequest) => {
  // ruleid: nextjs-ssrf
  await fetch(req.nextUrl.searchParams.get("u")!);
  return new Response("ok");
};

const assigned = async (req: NextRequest) => {
  // ruleid: nextjs-ssrf
  await fetch(req.nextUrl.searchParams.get("u")!);
  return new Response("ok");
};

// HTTP メソッドとして公開しない関数は、引数を検出しない
const notRoute = async (value: string) => {
  return fetch(value);
};

export { arrow as POST, GET, notRoute };
export const PUT = withAuth(wrapped);
export const PATCH = withAuth(wrappedArrow);
export const DELETE = assigned;
