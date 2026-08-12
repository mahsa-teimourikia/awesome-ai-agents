import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

export default defineConfig({
  root: "app",
  base: "/awsome-ai-agents/",
  plugins: [react()],
  build: { outDir: "../out", emptyOutDir: true },
});
