import tailwindcss from "@tailwindcss/vite";
import { tanstackStart } from "@tanstack/react-start/plugin/vite";
import viteReact from "@vitejs/plugin-react";
import { defineConfig } from "vite";
import tsConfigPaths from "vite-tsconfig-paths";

import { applyDotEnv } from "./dotenv";

export default defineConfig(() => {
  // Make .env values (STRIPE_*, SITE_URL, VERITY_*) visible to server code in
  // `vite dev` and `vite build`. Real environment variables always win.
  applyDotEnv(process.cwd());

  return {
    server: {
      port: 3000,
      host: true,
      // Accept any Host header so a reverse proxy never triggers "Blocked request".
      allowedHosts: true as const,
    },
    plugins: [
      tailwindcss(),
      tsConfigPaths({ projects: ["./tsconfig.json"] }),
      tanstackStart(),
      viteReact(),
    ],
    optimizeDeps: {
      exclude: ["@tanstack/react-start"],
    },
  };
});
