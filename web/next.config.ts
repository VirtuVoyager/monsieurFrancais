import type { NextConfig } from "next";

const apiUrl = process.env.API_URL ?? "http://localhost:8000";

const nextConfig: NextConfig = {
  output: "standalone",
  experimental: {
    // The API can take longer than the 30 s default: waking from sleep (migrate, seed, start)
    // and grading a whole speaking session.
    proxyTimeout: 120_000,
  },
  async rewrites() {
    return [
      { source: "/api/:path*", destination: `${apiUrl}/:path*` },
      { source: "/media/catalog/:path*", destination: `${apiUrl}/media/catalog/:path*` },
    ];
  },
};

export default nextConfig;
