import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";
import tailwindcss from "@tailwindcss/vite";
import path from "path";

export default defineConfig({
  plugins: [react(), tailwindcss()],
  resolve: {
    alias: {
      "@": path.resolve(__dirname, "./src"),
    },
  },
  base: "/static/",
  build: {
    outDir: "../app/static",
    emptyOutDir: true,
  },
  server: {
    port: 5173,
    proxy: {
      "/api": "http://localhost:5000",
      "/chat": "http://localhost:5000",
      "/sessions": "http://localhost:5000",
      "/session": "http://localhost:5000",
      "/search": "http://localhost:5000",
      "/kg": "http://localhost:5000",
      "/graph": "http://localhost:5000",
      "/yt": "http://localhost:5000",
    },
  },
});
