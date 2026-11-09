import { exec, execFile, execSync } from "node:child_process";
import { readFile } from "node:fs/promises";
import path from "node:path";
import { type NextRequest, NextResponse } from "next/server";
import { z } from "zod";
import { buildUrl } from "./build-url";
import { db } from "./db";

const API_BASE = "https://api.example.com";
const apiBase = "https://api.example.com";
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
  // ok: nextjs-ssrf
  await fetch(`${API_BASE}/users/${url}`);
  // ok: nextjs-ssrf
  await fetch(`${process.env.API_BASE}/users/${url}`);
  // ok: nextjs-ssrf
  await fetch(`${apiBase}/users/${url}`);
  // ok: nextjs-ssrf
  await fetch(new URL("/api/x", process.env.API_BASE));
  const TARGET = url;
  // ruleid: nextjs-ssrf
  await fetch(`${TARGET}/x`);
  // ruleid: nextjs-ssrf
  await fetch(`${buildUrl(url)}/x`);
  // ruleid: nextjs-ssrf
  await fetch(`${API_BASE}${url}`);
  // ruleid: nextjs-ssrf
  await fetch(new URL("/api/x", req.url));
  // ruleid: nextjs-ssrf
  await fetch(new URL(`/${url}`, req.url));
  // ruleid: nextjs-ssrf
  await fetch(new URL("/api/x", url));
  // ruleid: nextjs-ssrf
  await fetch(`https://${encodeURIComponent(url)}/x`);

  // ruleid: nextjs-path-traversal
  await readFile(`/data/${q.get("file")}`);
  // ruleid: nextjs-path-traversal
  await readFile(path.join(BASE, q.get("file")!));
  // ok: nextjs-path-traversal
  await readFile(path.join(BASE, path.basename(q.get("file")!)));
  // ok: nextjs-path-traversal
  await readFile("/data/fixed.txt");
  // ruleid: nextjs-path-traversal
  await readFile(`/data/${encodeURIComponent(q.get("file")!)}`);

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
  // ok: nextjs-sql-injection
  await db.query({ text: "SELECT * FROM t WHERE a = $1", values: [q.get("a")] });
  // ruleid: nextjs-sql-injection
  await db.query({ text: `SELECT * FROM t WHERE a = '${q.get("a")}'` });
  // ruleid: nextjs-sql-injection
  await db.execute({ sql: `SELECT * FROM t WHERE a = '${q.get("a")}'` });
  // ruleid: nextjs-sql-injection
  await db.query(`SELECT * FROM t WHERE a = '${encodeURIComponent(q.get("a")!)}'`);
  // ruleid: nextjs-sql-injection
  await db.query(`SELECT * FROM t WHERE a = '${path.basename(q.get("a")!)}'`);

  // ok: nextjs-open-redirect
  NextResponse.redirect(new URL("/login", req.url));
  // ok: nextjs-open-redirect
  NextResponse.redirect(new URL("/login", req.nextUrl));
  // ok: nextjs-open-redirect
  NextResponse.redirect(new URL(`/users/${q.get("id")}`, req.url));
  // ruleid: nextjs-open-redirect
  NextResponse.redirect(new URL(`/${q.get("id")}`, req.url));
  // ruleid: nextjs-open-redirect
  NextResponse.redirect(new URL(`//${q.get("id")}`, req.url));
  // ruleid: nextjs-open-redirect
  NextResponse.redirect(new URL("/" + q.get("id"), req.url));
  // ruleid: nextjs-open-redirect
  NextResponse.redirect(new URL("/x", `https://${req.headers.get("x-forwarded-host")}`));
  // ruleid: nextjs-open-redirect
  NextResponse.redirect(new URL("/x", q.get("base")!));
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
  // ok: nextjs-command-injection
  exec(`ls ${Number(dir)}`);
  // ruleid: nextjs-command-injection
  exec(`ls ${encodeURIComponent(dir)}`);
  // ruleid: nextjs-command-injection
  exec(`ls ${path.basename(dir)}`);

  // ruleid: nextjs-code-injection
  eval(body.code);
  // ruleid: nextjs-code-injection
  new Function("return 1", code);
  // ok: nextjs-code-injection
  eval("1 + 1");
  // ruleid: nextjs-code-injection
  eval(encodeURIComponent(code));

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
