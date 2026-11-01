import { createFileRoute } from "@tanstack/react-router";

export const Route = createFileRoute("/api/stripe-webhook")({
  server: {
    handlers: {
      POST: async ({ request }) => {
        const { handleWebhook, PaymentError } = await import("../../lib/payments.server");
        if (!process.env.STRIPE_WEBHOOK_SECRET || !process.env.STRIPE_SECRET_KEY) {
          return new Response("Webhook not configured", { status: 503 });
        }
        const body = await request.text(); // raw body: required for signature verification
        try {
          await handleWebhook(body, request.headers.get("stripe-signature"));
        } catch (err) {
          if (err instanceof PaymentError) return new Response(err.message, { status: 400 });
          console.error("[stripe-webhook] error:", err);
          return new Response("Webhook error", { status: 500 }); // Stripe retries 5xx
        }
        return new Response("ok", { status: 200 });
      },
    },
  },
});
