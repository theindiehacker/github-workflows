import DOMPurify from "isomorphic-dompurify";
import { cookies, headers } from "next/headers";
import { redirect } from "next/navigation";
import { db } from "./db";
import { withReturnTo } from "./with-return-to";

export default async function Page({
  searchParams,
  params,
}: {
  searchParams: Promise<{ q: string; next: string; u: string }>;
  params: Promise<{ id: string }>;
}) {
  const { q, next, u } = await searchParams;
  const { id } = await params;

  // ruleid: nextjs-open-redirect
  if (next) redirect(next);
  // ok: nextjs-open-redirect
  if (!q) redirect("/login");
  // ok: nextjs-open-redirect
  if (!q) redirect(`/items/${id}/detail`);
  const returnTo = `/items/${id}/detail`;
  // ok: nextjs-open-redirect
  if (!q) redirect(withReturnTo(returnTo));
  // ruleid: nextjs-open-redirect
  if (!q) redirect(`${next}/x`);
  // ruleid: nextjs-open-redirect
  if (!q) redirect(`//${next}`);
  // ruleid: nextjs-open-redirect
  if (!q) redirect(`/${next}`);
  // ruleid: nextjs-open-redirect
  if (!q) redirect(withReturnTo(next));
  // ruleid: nextjs-open-redirect
  if (!q) redirect(`/x` + next);
  // ruleid: nextjs-open-redirect
  if (!q) redirect(`/x`.concat(next));
  // ruleid: nextjs-open-redirect
  if (!q) redirect(`/x` || next);

  // ruleid: nextjs-ssrf
  await fetch(u);
  // ruleid: nextjs-sql-injection
  await db.query(`SELECT * FROM t WHERE id = ${id}`);

  const host = (await headers()).get("x-forwarded-host");
  // ruleid: nextjs-ssrf
  await fetch(`https://${host}/x`);

  const token = (await cookies()).get("t")?.value;
  // ruleid: nextjs-sql-injection
  await db.query(`SELECT * FROM t WHERE token = '${token}'`);

  // ok: nextjs-xss
  const text = <p>{q}</p>;
  // ok: nextjs-xss
  const fixed = <div dangerouslySetInnerHTML={{ __html: "<b>fixed</b>" }} />;
  // ok: nextjs-xss
  const clean = <div dangerouslySetInnerHTML={{ __html: DOMPurify.sanitize(q) }} />;
  // ruleid: nextjs-xss
  const dirty = <div dangerouslySetInnerHTML={{ __html: q }} />;
  // ruleid: nextjs-xss
  const encoded = <div dangerouslySetInnerHTML={{ __html: encodeURIComponent(q) }} />;
  const jsonLd = { "@context": "https://schema.org", name: q };
  // ruleid: nextjs-xss
  const ld = <script type="application/ld+json" dangerouslySetInnerHTML={{ __html: JSON.stringify(jsonLd) }} />;
  const safeLd = (
    <script
      type="application/ld+json"
      // ok: nextjs-xss
      dangerouslySetInnerHTML={{ __html: JSON.stringify(jsonLd).replace(/</g, "\\u003c") }}
    />
  );

  return (
    <>
      {text}
      {fixed}
      {clean}
      {dirty}
      {encoded}
      {ld}
      {safeLd}
    </>
  );
}

export async function deleteItem(id: string) {
  "use server";
  // ruleid: nextjs-sql-injection
  await db.query(`DELETE FROM items WHERE id = ${id}`);
}

export const removeItem = async (id: string) => {
  "use server";
  // ruleid: nextjs-sql-injection
  await db.query(`DELETE FROM items WHERE id = ${id}`);
};

export const findItem = async (id: string) => {
  // ok: nextjs-sql-injection
  return db.query(`SELECT * FROM items WHERE id = ${id}`);
};
