import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";
import tailwindcss from "@tailwindcss/vite";
import { fileURLToPath } from "node:url";

const srcPath = fileURLToPath(new URL("./src", import.meta.url));

export default defineConfig({
  plugins: [react(), tailwindcss()],
  resolve: {
    alias: {
      "@": srcPath,
    },
  },
  server: {
    host: "0.0.0.0",
    port: 5173,
    // The app is previewed through a sandbox proxy host, so any host is allowed
    // in development. Set VITE_ALLOWED_HOSTS to a comma-separated list to restrict it.
    allowedHosts: process.env.VITE_ALLOWED_HOSTS
      ? process.env.VITE_ALLOWED_HOSTS.split(",").map((host) => host.trim())
      : true,
    proxy: {
      // All API calls are relative; Vite proxies them to the FastAPI backend.
      "/api": {
        target: process.env.VITE_API_TARGET ?? "http://127.0.0.1:8000",
        changeOrigin: true,
      },
    },
  },
  build: {
    outDir: "dist",
    sourcemap: false,
  },
});
