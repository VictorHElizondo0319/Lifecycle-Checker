import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  /* config options here */
  // Export static files for Electron
  output: 'export',
  assetPrefix: "./",
  // trailingSlash: true,
  // Disable image optimization for Electron
  images: {
    unoptimized: true,
  },
  // Allow external images if needed
  async rewrites() {
    return [];
  },
};

export default nextConfig;
