import assert from "node:assert/strict";
import { test } from "node:test";

import { checkStripeKey } from "../src/lib/stripeKey.ts";

test("test keys are fine anywhere", () => {
  assert.equal(checkStripeKey("sk_test_abc", { NODE_ENV: "development" }).ok, true);
  assert.equal(checkStripeKey("rk_test_abc", { NODE_ENV: "production" }).ok, true);
});

test("live keys are blocked outside production", () => {
  for (const key of ["sk_live_abc", "rk_live_abc"]) {
    const result = checkStripeKey(key, { NODE_ENV: "development" });
    assert.equal(result.ok, false);
    assert.equal(checkStripeKey(key, {}).ok, false);
  }
});

test("live keys work in production, or when explicitly allowed", () => {
  assert.equal(checkStripeKey("sk_live_abc", { NODE_ENV: "production" }).ok, true);
  assert.equal(checkStripeKey("sk_live_abc", { NODE_ENV: "development", VERITY_ALLOW_LIVE_KEY_IN_DEV: "1" }).ok, true);
});

test("missing or malformed keys are rejected, and the key is never echoed", () => {
  assert.equal(checkStripeKey(undefined).ok, false);
  const bad = checkStripeKey("not-a-key-secret-value", { NODE_ENV: "development" });
  assert.equal(bad.ok, false);
  assert.ok(!("reason" in bad) || !bad.reason.includes("secret-value"));
});
