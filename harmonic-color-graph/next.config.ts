import type { NextConfig } from "next";

// Vercel doesn't interpolate env vars into the modern `rewrites` array in
// vercel.json (only the legacy `routes` config supports that, and mixing
// `routes` with the Next.js framework preset is discouraged) - so the
// same-origin API proxy is configured here instead, where `HCG_API_ORIGIN`
// is read at build time per environment (production/preview get their own
// value from Vercel project env vars; local dev falls back to the FastAPI
// dev server).
const HCG_API_ORIGIN = process.env.HCG_API_ORIGIN ?? "http://127.0.0.1:8000";

const nextConfig: NextConfig = {
  async rewrites() {
    return [
      {
        source: "/api/hcg/:path*",
        destination: `${HCG_API_ORIGIN}/:path*`,
      },
    ];
  },
};

export default nextConfig;
