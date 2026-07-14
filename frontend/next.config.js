/** @type {import('next').NextConfig} */
const nextConfig = {
  output: 'standalone',
  optimizeFonts: false,
  images: {
    domains: [],
  },
  async rewrites() {
    return [
      {
        source: '/api/:path*',
        destination: 'http://backend:8000/api/:path*',
      },
    ];
  },
};

module.exports = nextConfig;
