"use client";

import { useParams, usePathname, useRouter, useSearchParams } from "next/navigation";

export function Browser() {
  const q = new URLSearchParams(window.location.search).get("u")!;
  const { id } = useParams();
  const pathname = usePathname();
  const router = useRouter();
  const params = new URLSearchParams(useSearchParams());

  // ruleid: nextjs-xss
  const search = <div dangerouslySetInnerHTML={{ __html: q }} />;
  // ruleid: nextjs-xss
  const hash = <div dangerouslySetInnerHTML={{ __html: location.hash }} />;
  // ruleid: nextjs-xss
  const param = <div dangerouslySetInnerHTML={{ __html: String(id) }} />;
  // ruleid: nextjs-xss
  const referrer = <div dangerouslySetInnerHTML={{ __html: document.referrer }} />;

  // 先頭が usePathname() の値なら、同じサイトの中なので検出しない
  router.push(`${pathname}?tab=1`);
  router.push(`${pathname}?${params.toString()}`);
  router.push(`${pathname}/edit?${params}`);
  const sameSite = <a href={`${pathname}?${params}`}>x</a>;

  return (
    <>
      {search}
      {hash}
      {param}
      {referrer}
      {sameSite}
    </>
  );
}

export function NameIsNotEnough() {
  const sp = useSearchParams();
  const router = useRouter();
  // 変数名が pathname でも、中身がリクエストの値なら検出する
  const pathname = sp.get("next")!;

  // ruleid: nextjs-open-redirect
  router.push(`${pathname}/x`);
  // ruleid: nextjs-open-redirect
  router.push(`${pathname}?tab=1`);
  // ruleid: nextjs-open-redirect
  router.push(`${pathname}//evil.example`);
  // ruleid: nextjs-open-redirect
  router.push(`${pathname}`);
  // ruleid: nextjs-xss-url
  return <a href={`${pathname}?tab=1`}>x</a>;
}
