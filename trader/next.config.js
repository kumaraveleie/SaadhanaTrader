/** @type {import('next').NextConfig} */
const nextConfig = {
  reactStrictMode: true,
  async redirects() {
    // /research → /markets (renamed in K1 IA cleanup; bookmarks /
    // shared links survive). Permanent so search engines update the
    // canonical URL. /research is reserved for the future fundamental
    // analysis layer per spec §15.4.
    return [
      {
        source: '/research',
        destination: '/markets',
        permanent: true,
      },
      {
        source: '/research/:path*',
        destination: '/markets/:path*',
        permanent: true,
      },
    ];
  },
};

module.exports = nextConfig;
