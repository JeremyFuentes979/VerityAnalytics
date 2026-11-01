// Guard against using a LIVE Stripe key outside production (e.g. a live key
// left in .env while developing, which would create real charges).

export type KeyCheck = { ok: true } | { ok: false; reason: string };

export function checkStripeKey(
  key: string | undefined,
  env: { NODE_ENV?: string; VERITY_ALLOW_LIVE_KEY_IN_DEV?: string } = process.env,
): KeyCheck {
  if (!key) return { ok: false, reason: "Stripe is not configured." };
  if (!/^(sk|rk)_(test|live)_/.test(key)) {
    return { ok: false, reason: "STRIPE_SECRET_KEY is not a valid Stripe secret key (it should start with sk_test_ or sk_live_)." };
  }
  const isLive = /^(sk|rk)_live_/.test(key);
  if (isLive && env.NODE_ENV !== "production" && env.VERITY_ALLOW_LIVE_KEY_IN_DEV !== "1") {
    return {
      ok: false,
      reason: "A LIVE Stripe key is set while running in development. Use your sk_test_ key, or set VERITY_ALLOW_LIVE_KEY_IN_DEV=1 if you really mean to charge real cards.",
    };
  }
  return { ok: true };
}
