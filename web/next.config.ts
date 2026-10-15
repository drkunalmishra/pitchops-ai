import type { NextConfig } from "next";

// Local dev only: proxy /api/* to the Cloud Run API (in production Firebase Hosting does this rewrite).
const API_DEV = process.env.API_DEV_URL || "https://api-f7ju5n4lda-uc.a.run.app";

const nextConfig: NextConfig = {
  ...(process.env.NODE_ENV === "production" ? { output: "export" as const } : {}),
  images: { unoptimized: true },
  trailingSlash: true,
  ...(process.env.NODE_ENV !== "production"
    ? { rewrites: async () => [{ source: "/api/:path*", destination: `${API_DEV}/api/:path*` }] }
    : {}),
};

export default nextConfig;
