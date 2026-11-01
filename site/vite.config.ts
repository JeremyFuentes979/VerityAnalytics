import tailwindcss from "@tailwindcss/vite";
import { tanstackStart } from "@tanstack/react-start/plugin/vite";
import viteReact from "@vitejs/plugin-react";
import { defineConfig, loadEnv } from "vite";
import tsConfigPaths from "vite-tsconfig-paths";

export default defineConfig(({ mode }) => {
  // Make .env values (STRIPE_*, SITE_URL, VERITY_*) visible to server code in
  // `vite dev` and `vite build`. Real environment variables always win.
  const env = loadEnv(mode, process.cwd(), "");
  for (const [key, value] of Object.entries(env)) {
    if (process.env[key] === undefined) process.env[key] = value;
  }

  return {
    server: {
      port: 3000,
      host: true,
      // Accept any Host header so a reverse proxy never triggers "Blocked request".
      allowedHosts: true,
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
