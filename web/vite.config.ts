import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

export default defineConfig({
  plugins: [react()],
  // relative asset paths so the build can be hosted under any sub-path
  base: "./",
});
