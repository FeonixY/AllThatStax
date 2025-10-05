import { defineConfig, loadEnv } from "vite";
import react from "@vitejs/plugin-react";

export default defineConfig(({ mode }) => {
  const env = loadEnv(mode, process.cwd(), "VITE_");
  const apiBase = env.VITE_API_BASE_URL ?? "http://localhost:8000";

  return {
    plugins: [react()],
    server: {
      port: 5173,
      host: "0.0.0.0",
      proxy: {
        "/cards": {
          target: apiBase,
          changeOrigin: true,
        },
        "/metadata": {
          target: apiBase,
          changeOrigin: true,
        },
        "/images": {
          target: apiBase,
          changeOrigin: true,
        },
        "/symbols": {
          target: apiBase,
          changeOrigin: true,
        },
      },
    },
    build: {
      outDir: "dist",
      sourcemap: true,
    },
  };
});
