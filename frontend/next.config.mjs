/** @type {import('next').NextConfig} */
const nextConfig = {
  async rewrites() {
    // In production NEXT_PUBLIC_API_URL is set directly, so no rewrite needed.
    // In local dev (no env var), proxy /api/* to the local backend.
    if (process.env.NEXT_PUBLIC_API_URL) {
      return [];
    }
    return [
      {
        source: '/api/:path*',
        destination: 'http://localhost:8000/api/:path*',
      },
    ];
  },
};

export default nextConfig;
