import { exec, execFile, execSync } from "node:child_process";
import { readFile } from "node:fs/promises";
import path from "node:path";
import { type NextRequest, NextResponse } from "next/server";
import { z } from "zod";
import { buildUrl } from "./build-url";
import { db } from "./db";

const BASE = "/data";
const schema = z.object({ url: z.string() });

export async function GET(req: NextRequest) {
  const q = req.nextUrl.searchParams;
  const url = q.get("url")!;

  // ruleid: nextjs-ssrf
  await fetch(url);
  // ruleid: nextjs-ssrf
  await fetch(q.get("url")!);
  // ruleid: nextjs-ssrf
  await fetch(new URL(req.url).searchParams.get("u")!);
  // ruleid: nextjs-ssrf
  await fetch(`${url}/x`);
  // ruleid: nextjs-ssrf
  await fetch(buildUrl(url));
  // ok: nextjs-ssrf
  await fetch("https://api.example.com/x");
  // ok: nextjs-ssrf
  await fetch(`https://api.example.com/users/${url}`);
  // ok: nextjs-ssrf
  await fetch("https://api.example.com/x", { method: "POST", body: url });

  // ruleid: nextjs-path-traversal
  await readFile(`/data/${q.get("file")}`);
  // ruleid: nextjs-path-traversal
  await readFile(path.join(BASE, q.get("file")!));
  // ok: nextjs-path-traversal
  await readFile(path.join(BASE, path.basename(q.get("file")!)));
  // ok: nextjs-path-traversal
  await readFile("/data/fixed.txt");

  // ruleid: nextjs-sql-injection
  await db.query(`SELECT * FROM t WHERE a = '${q.get("a")}'`);
  // ruleid: nextjs-sql-injection
  await db.$queryRawUnsafe(`SELECT * FROM t WHERE a = '${q.get("a")}'`);
  // ok: nextjs-sql-injection
  await db.query("SELECT * FROM t WHERE a = $1", [q.get("a")]);
  // ok: nextjs-sql-injection
  await db.query({ query: "x", variables: { a: q.get("a") } });
  // ok: nextjs-sql-injection
  await db.query(`SELECT * FROM t WHERE a = ${Number(q.get("a"))}`);

  // ok: nextjs-open-redirect
  NextResponse.redirect(new URL("/login", req.url));
  // ok: nextjs-open-redirect
  NextResponse.redirect(new URL(`/users/${q.get("id")}`, req.url));
  // ruleid: nextjs-open-redirect
  return NextResponse.redirect(q.get("next")!);
}

export async function POST(req: NextRequest) {
  const body = await req.json();
  const { dir, code, target } = body;
  const parsed = schema.parse(body);

  // ruleid: nextjs-command-injection
  exec(`ls ${body.dir}`);
  // ruleid: nextjs-command-injection
  execSync(`ls ${dir}`);
  // ok: nextjs-command-injection
  execFile("ls", [dir]);
  // ok: nextjs-command-injection
  exec("ls");

  // ruleid: nextjs-code-injection
  eval(body.code);
  // ruleid: nextjs-code-injection
  new Function("return 1", code);
  // ok: nextjs-code-injection
  eval("1 + 1");

  // ruleid: nextjs-ssrf
  await fetch(target);
  // ruleid: nextjs-ssrf
  await fetch(parsed.url);
  await localFetch(target);

  return NextResponse.json({ ok: true });
}

export async function DELETE(req: NextRequest, { params }: { params: Promise<{ id: string }> }) {
  const { id } = await params;
  // ruleid: nextjs-sql-injection
  await db.query(`DELETE FROM t WHERE id = ${id}`);
  return new Response(null, { status: 204 });
}

export async function helper(value: string) {
  // ok: nextjs-ssrf
  return fetch(value);
}

async function localFetch(value: string) {
  // todoruleid: nextjs-ssrf
  return fetch(value);
}
