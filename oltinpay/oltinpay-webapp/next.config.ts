import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  output: 'standalone',
  // Disable image optimization for Telegram Mini App
  images: {
    unoptimized: true,
  },
};

export default nextConfig;
