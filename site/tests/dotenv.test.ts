import assert from "node:assert/strict";
import { mkdtempSync, writeFileSync } from "node:fs";
import { tmpdir } from "node:os";
import { join } from "node:path";
import { test } from "node:test";

import { applyDotEnv } from "../dotenv.ts";

test("editing .env and reloading in the same process updates values (the dev-server restart case)", () => {
  const dir = mkdtempSync(join(tmpdir(), "verity-env-"));
  delete process.env.T_BYPASS;
  delete process.env.T_REMOVED;
  writeFileSync(join(dir, ".env"), "T_BYPASS=1\nT_REMOVED=yes\n");
  applyDotEnv(dir);
  assert.equal(process.env.T_BYPASS, "1");

  writeFileSync(join(dir, ".env"), "T_BYPASS=0\n");
  applyDotEnv(dir);
  assert.equal(process.env.T_BYPASS, "0");
  assert.equal(process.env.T_REMOVED, undefined);
});

test("real environment variables are never overridden by .env", () => {
  const dir = mkdtempSync(join(tmpdir(), "verity-env-"));
  process.env.T_SHELL = "from-shell";
  writeFileSync(join(dir, ".env"), "T_SHELL=from-file\n");
  applyDotEnv(dir);
  applyDotEnv(dir);
  assert.equal(process.env.T_SHELL, "from-shell");
});
