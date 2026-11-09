"use client";

import { useRouter, useSearchParams } from "next/navigation";

export function Client() {
  const sp = useSearchParams();
  const router = useRouter();
  const next = sp.get("next")!;

  function go() {
    // ruleid: nextjs-open-redirect
    router.push(next);
    // ok: nextjs-open-redirect
    router.push("/home");
    // ruleid: nextjs-open-redirect
    window.location.href = next;
  }

  // ruleid: nextjs-xss
  const dirty = <span dangerouslySetInnerHTML={{ __html: sp.get("q")! }} />;

  return (
    <button type="button" onClick={go}>
      {dirty}
    </button>
  );
}
