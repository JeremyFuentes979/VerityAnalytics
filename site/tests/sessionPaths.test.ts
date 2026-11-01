import assert from "node:assert/strict";
import { test } from "node:test";

import { getSessionDir, isValidSessionId } from "../src/lib/sessionPaths.ts";

test("accepts real UUIDs", () => {
  assert.equal(isValidSessionId(crypto.randomUUID()), true);
});

test("rejects anything that is not a UUID", () => {
  for (const bad of ["", "abc", "../etc/passwd", "a/b", "x; rm -rf /", "$(id)", "00000000-0000-0000-0000-000000000000/..", null, undefined, 42]) {
    assert.equal(isValidSessionId(bad), false, String(bad));
  }
});

test("getSessionDir throws for invalid ids and stays inside the sessions dir", () => {
  process.env.VERITY_SESSIONS_DIR = "/tmp/verity-sessions";
  assert.throws(() => getSessionDir("../../etc"));
  const id = crypto.randomUUID();
  assert.equal(getSessionDir(id), `/tmp/verity-sessions/${id}`);
});
