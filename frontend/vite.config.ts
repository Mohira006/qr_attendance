import react from "@vitejs/plugin-react";
import { defineConfig } from "vite";

// Proxies /api and /ws to the backend during development so the frontend can
// use relative URLs and never hardcode a host/port.
export default defineConfig({
  plugins: [react()],
  resolve: {
    alias: {
      "@": "/src",
    },
  },
  server: {
    port: 5173,
    proxy: {
      "/api": {
        target: "http://localhost:8000",
        changeOrigin: true,
      },
      "/ws": {
        target: "ws://localhost:8000",
        ws: true,
      },
    },
  },
});
