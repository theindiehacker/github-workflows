"use client";

import { useParams, useRouter, useSearchParams } from "next/navigation";

export const publicEnv = {
  // ruleid: nextjs-public-env-secret
  stripe: process.env.NEXT_PUBLIC_STRIPE_SECRET_KEY,
  // ruleid: nextjs-public-env-secret
  supabase: process.env.NEXT_PUBLIC_SUPABASE_SERVICE_ROLE_KEY,
  // ruleid: nextjs-public-env-secret
  sentry: process.env["NEXT_PUBLIC_SENTRY_AUTH_TOKEN"],
  // ruleid: nextjs-public-env-secret
  aws: process.env.NEXT_PUBLIC_AWS_SECRET_ACCESS_KEY,
  // ok: nextjs-public-env-secret
  mapbox: process.env.NEXT_PUBLIC_MAPBOX_TOKEN,
  // ok: nextjs-public-env-secret
  mapboxAccess: process.env.NEXT_PUBLIC_MAPBOX_ACCESS_TOKEN,
  // ok: nextjs-public-env-secret
  datadog: process.env.NEXT_PUBLIC_DATADOG_CLIENT_TOKEN,
  // ok: nextjs-public-env-secret
  publishable: process.env.NEXT_PUBLIC_STRIPE_PUBLISHABLE_KEY,
  // ok: nextjs-public-env-secret
  privateBeta: process.env.NEXT_PUBLIC_IS_PRIVATE_BETA,
  // ok: nextjs-public-env-secret
  tokenUrl: process.env.NEXT_PUBLIC_OAUTH_TOKEN_URL,
  // ok: nextjs-public-env-secret
  server: process.env.STRIPE_SECRET_KEY,
};

export function Client() {
  const sp = useSearchParams();
  const router = useRouter();
  const next = sp.get("next")!;
  const { slug } = useParams<{ slug: string }>();

  function go() {
    // ruleid: nextjs-open-redirect
    router.push(next);
    // ok: nextjs-open-redirect
    router.push("/home");
    // ruleid: nextjs-open-redirect
    window.location.href = next;
    // ruleid: nextjs-open-redirect
    router.push(slug);
    // ruleid: nextjs-open-redirect
    location.href = slug;
    // ruleid: nextjs-open-redirect
    location.assign(next);
    // ruleid: nextjs-open-redirect
    window.open(next);
    // ok: nextjs-open-redirect
    window.open("/help");
  }

  // ruleid: nextjs-xss
  const dirty = <span dangerouslySetInnerHTML={{ __html: sp.get("q")! }} />;

  return (
    <button type="button" onClick={go}>
      {dirty}
    </button>
  );
}
