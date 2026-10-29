import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  reactStrictMode: true,
  // A small self-contained server for the Docker image.
  output: "standalone",
};

export default nextConfig;
