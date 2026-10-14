import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  output: "standalone",
  turbopack: {
    rules: {
      // Feedback: every element knows which file and line it comes from (see feedback-source-loader.cjs).
      "*.tsx": { loaders: ["./feedback-source-loader.cjs"] },
    },
  },
};

export default nextConfig;
