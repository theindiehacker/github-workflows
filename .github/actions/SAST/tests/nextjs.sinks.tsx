import child_process, { execFile, exec as execCb, spawn } from "node:child_process";
import cp from "node:child_process";
import fs from "node:fs";
import { stat } from "node:fs/promises";
import http from "node:http";
import https from "node:https";
import path from "node:path";
import { promisify } from "node:util";
import vm from "node:vm";
import axios from "axios";
import got from "got";
import DOMPurify from "isomorphic-dompurify";
import Link from "next/link";
import { type NextRequest, NextResponse } from "next/server";
import { undici } from "undici";
import { db, Prisma, qb, sql } from "./db";

const BASE = "/data";
const execAsync = promisify(execCb);

export async function GET(req: NextRequest) {
  const u = req.nextUrl.searchParams.get("u")!;
  const el = document.body;
  const headers = new Headers();

  // ruleid: nextjs-ssrf
  http.get(u);
  // ruleid: nextjs-ssrf
  https.request(u);
  // ruleid: nextjs-ssrf
  undici.request(u);
  // ruleid: nextjs-ssrf
  globalThis.fetch(u);
  // ruleid: nextjs-ssrf
  await axios.post(u, {});
  // ruleid: nextjs-ssrf
  got.stream(u);
  // ruleid: nextjs-ssrf
  await axios.postForm(u, {});
  // ruleid: nextjs-ssrf
  axios.create({ baseURL: u });
  // ok: nextjs-ssrf
  await axios.post("https://api.example.com/x", { u });

  // ruleid: nextjs-rewrite
  NextResponse.rewrite(u);
  // ruleid: nextjs-rewrite
  NextResponse.rewrite(new URL(u));
  // ruleid: nextjs-rewrite
  NextResponse.rewrite(new URL(u, req.url));
  // ruleid: nextjs-rewrite
  NextResponse.rewrite(`https://${encodeURIComponent(u)}/x`);
  // ok: nextjs-rewrite
  NextResponse.rewrite(new URL("/maintenance", req.url));
  // ok: nextjs-rewrite
  NextResponse.rewrite(new URL(`/items/${u}/x`, req.url));

  // ruleid: nextjs-command-injection
  spawn(u, { shell: true });
  // ruleid: nextjs-command-injection
  spawn("ls", [u], { shell: true });
  // ruleid: nextjs-command-injection
  spawn("sh", ["-c", u]);
  // ruleid: nextjs-command-injection
  spawn(u);
  // ruleid: nextjs-command-injection
  execFile(u, []);
  // ruleid: nextjs-command-injection
  execAsync(`ls ${u}`);
  // ruleid: nextjs-command-injection
  child_process.spawn("ls", [u], { shell: true });
  // ruleid: nextjs-command-injection
  cp.spawn("sh", ["-c", u]);
  // ruleid: nextjs-command-injection
  spawn("ls", [u], { shell: "/bin/bash" });
  // ruleid: nextjs-command-injection
  spawn("bash", ["-lc", u]);
  // ok: nextjs-command-injection
  spawn("ls", [u], { shell: false });
  // ok: nextjs-command-injection
  spawn("ls", [u]);
  // ok: nextjs-command-injection
  execFile("ls", [u]);

  // ruleid: nextjs-path-traversal
  fs.copyFile(u, "x", () => {});
  // ruleid: nextjs-path-traversal
  fs.copyFile("x", u, () => {});
  // ruleid: nextjs-path-traversal
  fs.readdir(u, () => {});
  // ruleid: nextjs-path-traversal
  fs.appendFile(u, "x", () => {});
  // ruleid: nextjs-path-traversal
  fs.rename(u, "x", () => {});
  // ruleid: nextjs-path-traversal
  fs.promises.open(u);
  // ruleid: nextjs-path-traversal
  fs.stat(u, () => {});
  // ruleid: nextjs-path-traversal
  await stat(u);
  // ruleid: nextjs-path-traversal
  fs.rename("x", u, () => {});
  // ruleid: nextjs-path-traversal
  fs.cp("x", u, () => {});
  // ruleid: nextjs-path-traversal
  fs.symlink("x", u, () => {});
  // ruleid: nextjs-path-traversal
  rm(u);
  // ruleid: nextjs-path-traversal
  anyFs.rm(u);
  // ok: nextjs-path-traversal
  fs.writeFile("x", u, () => {});
  // ok: nextjs-path-traversal
  dialog.open(u);
  // ok: nextjs-path-traversal
  cache.stat(u);
  // ok: nextjs-path-traversal
  fs.readFile(path.join(BASE, path.basename(u)), () => {});

  // ruleid: nextjs-code-injection
  vm.runInNewContext(u);
  // ruleid: nextjs-code-injection
  vm.runInThisContext(u);
  // ruleid: nextjs-code-injection
  new vm.Script(u);
  // ruleid: nextjs-code-injection
  setTimeout(u, 0);
  // ruleid: nextjs-code-injection
  setInterval(u, 1);
  // ruleid: nextjs-code-injection
  await import(u);
  // ruleid: nextjs-code-injection
  require(u);
  // ok: nextjs-code-injection
  setTimeout(() => console.log(u), 0);
  // ok: nextjs-code-injection
  setTimeout(async () => console.log(u), 0);
  // ok: nextjs-code-injection
  setTimeout(function () { console.log(u); }, 0);
  // ok: nextjs-code-injection
  await import("./fixed");
  // ok: nextjs-code-injection
  require("./fixed");

  // ruleid: nextjs-sql-injection
  db.prepare(`SELECT ${u}`);
  // ruleid: nextjs-sql-injection
  db.run(`INSERT INTO t VALUES (${u})`);
  // ruleid: nextjs-sql-injection
  db.exec(`SELECT ${u}`);
  // ruleid: nextjs-sql-injection
  db.all(`select ${u}`);
  // ruleid: nextjs-sql-injection
  db.get(`SELECT ${u}`);
  // ruleid: nextjs-sql-injection
  qb.whereRaw(`a = ${u}`);
  // ruleid: nextjs-sql-injection
  qb.orderByRaw(u);
  // ruleid: nextjs-sql-injection
  db.$queryRaw(Prisma.raw(u));
  // ruleid: nextjs-sql-injection
  sql.raw(u);
  // ok: nextjs-sql-injection
  new Map().get(u);
  // ok: nextjs-sql-injection
  /a/.exec(u);
  // ok: nextjs-sql-injection
  db.get("SELECT 1 WHERE a = ?", [u]);
  // ok: nextjs-sql-injection
  db.prepare("SELECT 1 WHERE a = ?").get(u);

  // ruleid: nextjs-open-redirect
  location.href = u;
  // ruleid: nextjs-open-redirect
  window.location = u;
  // ruleid: nextjs-open-redirect
  location = u;
  // ruleid: nextjs-open-redirect
  document.location.href = u;
  // ruleid: nextjs-open-redirect
  location.assign(u);
  // ruleid: nextjs-open-redirect
  location.replace(u);
  // ruleid: nextjs-open-redirect
  window.open(u);
  // ruleid: nextjs-open-redirect
  new Response(null, { status: 302, headers: { Location: u } });
  // ruleid: nextjs-open-redirect
  headers.set("Location", u);
  // ruleid: nextjs-open-redirect
  redirect(`https://${encodeURIComponent(u)}/x`);
  // ruleid: nextjs-open-redirect
  router.push({ pathname: u });
  // ok: nextjs-open-redirect
  redirect(`/x?r=${encodeURIComponent(u)}`);
  // ok: nextjs-open-redirect
  router.push({ pathname: "/x", query: { u } });
  // ok: nextjs-open-redirect
  location.href = "/x";
  // ok: nextjs-open-redirect
  window.open("/x");
  // ok: nextjs-open-redirect
  router.push(`?q=${u}`);
  // ok: nextjs-open-redirect
  headers.set("X-Foo", u);
  // ok: nextjs-open-redirect
  headers.set("Location", "/x");

  // ruleid: nextjs-xss
  document.write(u);
  // ruleid: nextjs-xss
  document.writeln(u);
  // ruleid: nextjs-xss
  el.innerHTML = u;
  // ruleid: nextjs-xss
  el.outerHTML = u;
  // ruleid: nextjs-xss
  el.insertAdjacentHTML("beforeend", u);
  // ruleid: nextjs-xss
  new Response(u, { headers: { "Content-Type": "text/html" } });
  // ruleid: nextjs-xss
  new NextResponse(u, { headers: { "content-type": "text/html; charset=utf-8" } });
  // ruleid: nextjs-xss
  const props = { dangerouslySetInnerHTML: { __html: u } };
  // ruleid: nextjs-xss
  const inTemplate = <div dangerouslySetInnerHTML={{ __html: `<b>${u}</b>` }} />;
  // ruleid: nextjs-xss
  const doc = <iframe srcDoc={u} />;
  // ruleid: nextjs-xss
  const docPath = <iframe srcDoc={`/x${u}`} />;
  // ok: nextjs-xss
  new Response(u, { headers: { "Content-Type": "text/plain" } });
  // ok: nextjs-xss
  el.textContent = u;
  // ok: nextjs-xss
  el.innerHTML = DOMPurify.sanitize(u);

  // ruleid: nextjs-xss-url
  const a = <a href={u}>x</a>;
  // ruleid: nextjs-xss-url
  const link = <Link href={u}>x</Link>;
  // ruleid: nextjs-xss-url
  const frame = <iframe src={u} />;
  // ruleid: nextjs-xss-url
  const objectPath = <Link href={{ pathname: u }}>x</Link>;
  // ruleid: nextjs-xss-url
  const objectHost = <Link href={{ protocol: "https", host: u }}>x</Link>;
  // ruleid: nextjs-xss-url
  const encodedHost = <a href={`https://${encodeURIComponent(u)}/x`}>x</a>;
  // ok: nextjs-xss-url
  const fixedPath = <a href={`/items/${u}`}>x</a>;
  // ok: nextjs-xss-url
  const queryOnly = <a href={`?q=${u}`}>x</a>;
  // ok: nextjs-xss-url
  const objectHref = <Link href={{ pathname: "/x", query: { u } }}>x</Link>;
  // ok: nextjs-xss-url
  const image = <img src={u} alt="" />;

  return (
    <>
      {props.dangerouslySetInnerHTML.__html}
      {inTemplate}
      {a}
      {link}
      {frame}
      {doc}
      {docPath}
      {objectPath}
      {objectHost}
      {encodedHost}
      {fixedPath}
      {queryOnly}
      {objectHref}
      {image}
    </>
  );
}
