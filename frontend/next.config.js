/** @type {import('next').NextConfig} */
const nextConfig = {
  output: "standalone",
  async rewrites() {
    // BACKEND_INTERNAL_URL: server-side only (Docker: http://backend:8000)
    // NEXT_PUBLIC_API_URL: client-side fallback for dev (http://localhost:8000)
    const backendUrl = process.env.BACKEND_INTERNAL_URL
      || process.env.NEXT_PUBLIC_API_URL
      || 'http://localhost:8000';
    return [
      {
        source: '/api/:path*',
        destination: `${backendUrl}/api/:path*`,
      },
    ];
  },
};

module.exports = nextConfig;
