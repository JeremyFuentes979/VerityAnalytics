import Stripe from "stripe";

import { BRAND, CURRENCY, PRICE_CENTS } from "./config";
import { isValidSessionId } from "./sessionPaths";
import { checkStripeKey } from "./stripeKey";
import { readSession, writeSession, WORKFLOW_RUNNING } from "./sessions.server";
import { startWorkflow } from "./workflow.server";

const CHECKOUT_ID_RE = /^cs_(test|live)_[A-Za-z0-9]{10,200}$/;

/** Local-testing shortcut. Can never be active in production. */
export function devBypassEnabled(): boolean {
  return process.env.VERITY_DEV_PAYMENT_BYPASS === "1" && process.env.NODE_ENV !== "production";
}

export function stripeConfigured(): boolean {
  return Boolean(process.env.STRIPE_SECRET_KEY);
}

export class PaymentError extends Error {}

/** Why Stripe can't be used right now, or null when the configured key is fine. */
export function stripeKeyProblem(): string | null {
  const check = checkStripeKey(process.env.STRIPE_SECRET_KEY);
  return check.ok ? null : check.reason;
}

function getStripe(): Stripe {
  const problem = stripeKeyProblem();
  if (problem) throw new PaymentError(problem);
  return new Stripe(process.env.STRIPE_SECRET_KEY as string);
}

/**
 * Record that a session is paid and kick off the workflow. Idempotent: the webhook
 * and the success-page check can both call this for the same payment.
 */
export async function markPaidAndStart(
  sessionId: string,
  payment: { stripeCheckoutSessionId?: string; amountPaid?: number; devBypass?: boolean },
): Promise<void> {
  const session = await readSession(sessionId);
  if (!session) throw new PaymentError("Session not found");

  if (!session.paidAt) {
    session.paidAt = new Date().toISOString();
    session.status = "paid";
    session.detail = "Payment received. The firm is starting.";
    if (payment.stripeCheckoutSessionId) session.stripeCheckoutSessionId = payment.stripeCheckoutSessionId;
    if (typeof payment.amountPaid === "number") session.amountPaid = payment.amountPaid;
    if (payment.devBypass) session.devBypass = true;
    await writeSession(session);
  }

  const fresh = (await readSession(sessionId)) ?? session;
  if (fresh.status === "complete" || WORKFLOW_RUNNING.has(fresh.status)) return;
  startWorkflow(sessionId, "full");
}

/** Only a fully paid, correctly priced Checkout Session may unlock a workflow. */
function assertPaidCheckout(checkout: Stripe.Checkout.Session, sessionId: string): void {
  if (checkout.mode !== "payment") throw new PaymentError("Unexpected checkout mode");
  if (checkout.client_reference_id !== sessionId) throw new PaymentError("Checkout does not match this session");
  if (checkout.payment_status !== "paid") throw new PaymentError("Payment is not complete");
  if (checkout.currency !== CURRENCY || (checkout.amount_total ?? 0) < PRICE_CENTS) {
    throw new PaymentError("Payment amount does not match the price");
  }
}

export async function createCheckoutUrl(sessionId: string, origin: string): Promise<string> {
  if (!isValidSessionId(sessionId)) throw new PaymentError("Invalid session");
  const checkout = await getStripe().checkout.sessions.create({
    mode: "payment",
    client_reference_id: sessionId,
    metadata: { sessionId },
    line_items: [
      {
        quantity: 1,
        price_data: {
          currency: CURRENCY,
          unit_amount: PRICE_CENTS,
          product_data: {
            name: `${BRAND} - Firm Hire`,
            description: "Full analysis: data cleaning, audit trail, decision memo and Excel workbook.",
          },
        },
      },
    ],
    success_url: `${origin}/results/${sessionId}?cs={CHECKOUT_SESSION_ID}`,
    cancel_url: `${origin}/checkout/${sessionId}?canceled=1`,
  });
  if (!checkout.url) throw new PaymentError("Stripe did not return a checkout URL");

  const session = await readSession(sessionId);
  if (session) {
    session.stripeCheckoutSessionId = checkout.id;
    await writeSession(session);
  }
  return checkout.url;
}

/** Called from the post-payment redirect: verify with Stripe, then unlock. */
export async function confirmCheckout(sessionId: string, checkoutId: string): Promise<void> {
  if (!CHECKOUT_ID_RE.test(checkoutId)) throw new PaymentError("Invalid checkout id");
  const checkout = await getStripe().checkout.sessions.retrieve(checkoutId);
  assertPaidCheckout(checkout, sessionId);
  await markPaidAndStart(sessionId, { stripeCheckoutSessionId: checkout.id, amountPaid: checkout.amount_total ?? undefined });
}

/** Verify a webhook delivery and fulfil it. Throws PaymentError on bad signatures. */
export async function handleWebhook(rawBody: string, signature: string | null): Promise<void> {
  const secret = process.env.STRIPE_WEBHOOK_SECRET;
  if (!secret) throw new Error("STRIPE_WEBHOOK_SECRET is not set");
  if (!signature) throw new PaymentError("Missing signature");

  let event: Stripe.Event;
  try {
    event = getStripe().webhooks.constructEvent(rawBody, signature, secret);
  } catch {
    throw new PaymentError("Invalid signature");
  }

  if (event.type !== "checkout.session.completed" && event.type !== "checkout.session.async_payment_succeeded") return;

  const checkout = event.data.object as Stripe.Checkout.Session;
  const sessionId = checkout.client_reference_id;
  if (!sessionId || !isValidSessionId(sessionId)) return;
  assertPaidCheckout(checkout, sessionId);
  await markPaidAndStart(sessionId, { stripeCheckoutSessionId: checkout.id, amountPaid: checkout.amount_total ?? undefined });
}
