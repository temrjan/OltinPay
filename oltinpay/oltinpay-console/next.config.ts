import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  // Server runtime required (E2): route handlers hold BANK_HMAC_SECRET and sign
  // bank requests server-side — never a static export.
  reactStrictMode: true,
};

export default nextConfig;
