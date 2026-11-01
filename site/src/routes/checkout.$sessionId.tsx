import { createFileRoute, Link, redirect } from "@tanstack/react-router";
import { createServerFn } from "@tanstack/react-start";
import { useState } from "react";

import { PRICE_DISPLAY } from "../lib/config";

const getCheckoutState = createServerFn({ method: "GET" })
  .validator((d: { sessionId: string }) => ({ sessionId: String(d.sessionId) }))
  .handler(async ({ data }) => {
    const { readSession } = await import("../lib/sessions.server");
    const session = await readSession(data.sessionId);
    if (!session) return { state: "missing" as const };
    if (session.paidAt) return { state: "paid" as const };
    if (session.status !== "profiled") return { state: "not_ready" as const };
    return { state: "ready" as const, fileName: session.fileName };
  });

type CheckoutResult = { url: string } | { error: string };

const startCheckout = createServerFn({ method: "POST" })
  .validator((d: { sessionId: string }) => ({ sessionId: String(d.sessionId) }))
  .handler(async ({ data }): Promise<CheckoutResult> => {
    const { readSession } = await import("../lib/sessions.server");
    const { createCheckoutUrl, devBypassEnabled, markPaidAndStart, stripeConfigured, stripeKeyProblem } = await import("../lib/payments.server");
    const session = await readSession(data.sessionId);
    if (!session) return { error: "This session no longer exists. Please upload your file again." };
    if (session.paidAt) return { url: `/results/${data.sessionId}` };
    if (session.status !== "profiled") return { error: "Your data is still being profiled. Please wait a moment." };

    if (devBypassEnabled()) {
      await markPaidAndStart(data.sessionId, { devBypass: true });
      return { url: `/results/${data.sessionId}` };
    }
    if (!stripeConfigured()) return { error: "Payments are not set up yet. Please try again later." };
    const keyProblem = stripeKeyProblem();
    if (keyProblem) {
      console.error(`[checkout] ${keyProblem}`);
      // Safe to show: this only ever describes a configuration mistake, never a key.
      return { error: process.env.NODE_ENV === "production" ? "Payments are not set up correctly. Please try again later." : keyProblem };
    }

    try {
      const { getRequestUrl } = await import("@tanstack/react-start/server");
      const origin = process.env.SITE_URL?.replace(/\/+$/, "") || getRequestUrl().origin;
      return { url: await createCheckoutUrl(data.sessionId, origin) };
    } catch (err) {
      console.error("[checkout] could not create Stripe session:", err);
      return { error: "We couldn't start checkout. Please try again in a moment." };
    }
  });

export const Route = createFileRoute("/checkout/$sessionId")({
  validateSearch: (search: Record<string, unknown>): { canceled?: boolean } =>
    search.canceled === "1" || search.canceled === 1 || search.canceled === true ? { canceled: true } : {},
  loader: async ({ params }) => {
    const result = await getCheckoutState({ data: { sessionId: params.sessionId } });
    if (result.state === "paid") throw redirect({ to: "/results/$sessionId", params: { sessionId: params.sessionId } });
    if (result.state === "not_ready") throw redirect({ to: "/preview/$sessionId", params: { sessionId: params.sessionId } });
    return result;
  },
  component: Checkout,
});

const deliverables = [
  { icon: "🧹", title: "Deep Data Cleaning", desc: "Duplicate removal, whitespace and category standardization by the Auditor" },
  { icon: "📊", title: "Full Analysis", desc: "Pattern analysis, anomaly detection, and metrics by the Analyst" },
  { icon: "🔍", title: "Audit Trail", desc: "Every correction logged, timestamped, and explained" },
  { icon: "📋", title: "Decision Memo", desc: "Clear recommendations synthesized by the Manager" },
  { icon: "📑", title: "Excel Workbook", desc: "Cleaned data, analysis, and audit trail in one professional file" },
];

function Checkout() {
  const data = Route.useLoaderData();
  const { sessionId } = Route.useParams();
  const { canceled } = Route.useSearch();
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  if (data.state === "missing") {
    return (
      <div className="mx-auto max-w-2xl px-8 py-24 text-center">
        <p className="font-serif text-2xl font-bold text-navy">Engagement Not Found</p>
        <Link to="/upload" className="mt-6 inline-block rounded-sm bg-navy px-6 py-2.5 text-sm font-medium text-white hover:bg-navy-700">
          Submit New Data
        </Link>
      </div>
    );
  }

  const handleHire = async () => {
    setBusy(true);
    setError(null);
    try {
      const result = await startCheckout({ data: { sessionId } });
      if ("error" in result) {
        setError(result.error);
        setBusy(false);
        return;
      }
      window.location.href = result.url;
    } catch {
      setError("Something went wrong. Please try again.");
      setBusy(false);
    }
  };

  return (
    <div className="mx-auto max-w-2xl px-8 py-16">
      <div className="text-center">
        <span className="inline-block rounded-sm border border-navy-200 px-3 py-1 text-xs font-medium uppercase tracking-[0.15em] text-navy-500">
          Engagement
        </span>
        <h1 className="mt-4 font-serif text-3xl font-bold text-navy sm:text-4xl">Hire the Firm</h1>
        <p className="mt-2 text-navy-500">Your data has been profiled. Engage the full firm for a comprehensive analysis.</p>
      </div>

      {canceled && (
        <div className="mt-6 rounded-sm border border-amber-200 bg-amber-50 p-4 text-center text-sm text-amber-800">
          Checkout was canceled. You haven&rsquo;t been charged.
        </div>
      )}

      <div className="mt-10 rounded-sm border border-navy-100">
        <div className="p-8">
          <h2 className="text-sm font-bold uppercase tracking-wider text-navy">Deliverables</h2>
          <ul className="mt-6 space-y-4">
            {deliverables.map((item) => (
              <li key={item.title} className="flex gap-4">
                <span className="mt-0.5 text-lg">{item.icon}</span>
                <div>
                  <p className="text-sm font-medium text-navy">{item.title}</p>
                  <p className="text-xs text-navy-500">{item.desc}</p>
                </div>
              </li>
            ))}
          </ul>
        </div>

        <div className="border-t border-navy-100 p-8 text-center">
          <p className="font-serif text-4xl font-bold text-navy">
            {PRICE_DISPLAY} <span className="text-base font-normal text-navy-500">USD</span>
          </p>
          <p className="mt-1 text-xs text-navy-500">One-time payment. No recurring fees.</p>
          <button
            onClick={handleHire}
            disabled={busy}
            className="mt-6 w-full rounded-sm bg-navy px-8 py-3.5 text-sm font-semibold uppercase tracking-wider text-white transition-colors hover:bg-navy-700 disabled:cursor-not-allowed disabled:opacity-50"
          >
            {busy ? (
              <span className="flex items-center justify-center gap-2">
                <span className="h-4 w-4 animate-spin rounded-full border-2 border-white border-t-transparent" />
                Processing
              </span>
            ) : (
              `Pay ${PRICE_DISPLAY} & Engage the Firm`
            )}
          </button>
          {error && (
            <p role="alert" className="mt-4 rounded-sm border border-red-200 bg-red-50 p-3 text-sm text-red-700">
              {error}
            </p>
          )}
          <p className="mt-3 text-xs text-navy-500">Secure checkout via Stripe. You will be redirected to complete payment.</p>
        </div>
      </div>

      <div className="mt-8 text-center">
        <Link to="/preview/$sessionId" params={{ sessionId }} className="text-xs text-navy-500 underline hover:text-navy">
          &larr; Return to data profile
        </Link>
      </div>
    </div>
  );
}
