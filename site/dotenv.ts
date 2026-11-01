import { existsSync, readFileSync } from "node:fs";
import { join } from "node:path";
import { parseEnv } from "node:util";

const MARK = "__VERITY_DOTENV_KEYS";

/**
 * Load .env / .env.local into process.env for server code.
 *
 * - Variables set by the real environment (shell, hosting provider) always win.
 * - Values we loaded ourselves are refreshed on every call, so editing .env while
 *   `vite dev` is running takes effect when the dev server restarts. (Vite restarts
 *   inside the same Node process, so a naive "only set if undefined" keeps stale values.)
 * - Keys deleted from .env are removed again.
 */
export function applyDotEnv(dir: string): void {
  const fromFile: Record<string, string> = {};
  for (const name of [".env", ".env.local"]) {
    const path = join(dir, name);
    if (existsSync(path)) Object.assign(fromFile, parseEnv(readFileSync(path, "utf8")));
  }

  const ours = new Set((process.env[MARK] ?? "").split(",").filter(Boolean));
  for (const key of ours) {
    if (!(key in fromFile)) {
      delete process.env[key];
      ours.delete(key);
    }
  }
  for (const [key, value] of Object.entries(fromFile)) {
    if (process.env[key] === undefined || ours.has(key)) {
      process.env[key] = value;
      ours.add(key);
    }
  }
  process.env[MARK] = [...ours].join(",");
}
