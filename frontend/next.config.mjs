/** @type {import('next').NextConfig} */
const backend = process.env.BACKEND_URL || "http://localhost:8000";
const onVercel = Boolean(process.env.VERCEL);

const nextConfig = {
  // Docker image needs the self-contained server; Vercel builds its own output.
  ...(process.env.DOCKER_BUILD ? { output: "standalone" } : {}),
  poweredByHeader: false,
  eslint: { ignoreDuringBuilds: true }, // lint runs as its own CI step
  // Same-origin API. On Vercel, /api/* is routed to the FastAPI service by vercel.json;
  // locally and in Docker, Next proxies /api/* to the backend so the httpOnly cookie just works.
  async rewrites() {
    return onVercel ? [] : [{ source: "/api/:path*", destination: `${backend}/api/:path*` }];
  },
};

export default nextConfig;
