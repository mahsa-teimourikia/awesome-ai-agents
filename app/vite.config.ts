import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

export default defineConfig({
  root: ".",
  base: "/awesome-ai-agents/",
  plugins: [react()],
  build: { outDir: "../out", emptyOutDir: true },
});
