import type { NextConfig } from "next";

const config: NextConfig = {
  images: {
    remotePatterns: [
      // ruleid: nextjs-image-any-host
      { protocol: "https", hostname: "**" },
      // ruleid: nextjs-image-any-host
      { hostname: "**", pathname: "/avatars/**" },
      // ruleid: nextjs-image-any-host
      new URL("https://**/images/**"),
      // ok: nextjs-image-any-host
      { protocol: "https", hostname: "images.example.com" },
      // ok: nextjs-image-any-host
      { protocol: "https", hostname: "**.example.com" },
      // ok: nextjs-image-any-host
      new URL("https://images.example.com/**"),
    ],
  },
};

const local: NextConfig = {
  // ruleid: nextjs-image-any-host
  images: { dangerouslyAllowLocalIP: true },
};

const safe: NextConfig = {
  // ok: nextjs-image-any-host
  images: { dangerouslyAllowLocalIP: false },
};

export default { config, local, safe };
