import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

export default defineConfig({
  plugins: [react()],
  server: {
    port: 5173,
    proxy: {
      "/contacts": "http://127.0.0.1:8000",
      "/messages": "http://127.0.0.1:8000",
      "/emails": "http://127.0.0.1:8000",
      "/phone": "http://127.0.0.1:8000"
    }
  },
  build: {
    outDir: "dist",
    emptyOutDir: true
  }
});
