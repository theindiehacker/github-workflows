"use server";

import { redirect } from "next/navigation";
import { db } from "./db";

export async function search(formData: FormData) {
  const term = formData.get("term");
  // ruleid: nextjs-sql-injection
  await db.query(`SELECT * FROM t WHERE a = '${term}'`);
  // ok: nextjs-sql-injection
  await db.query("SELECT * FROM t WHERE a = $1", [term]);
  // ruleid: nextjs-open-redirect
  redirect(String(formData.get("next")));
}

export const load = async (url: string) => {
  // ruleid: nextjs-ssrf
  return fetch(url);
};
