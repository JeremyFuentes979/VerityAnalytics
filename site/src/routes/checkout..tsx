import { createFileRoute, Link } from "@tanstack/react-router";
import { createServerFn } from "@tanstack/react-start";
import { useState } from "react";

const STRIPE_LINK = "https://buy.stripe.com/8x27sLeW73HJdlxfmdfnO00";

const hireFirm = createServerFn({ method: "POST" })
  .validator((d: unknown) => ({ sessionId: String(d) }))
  .handler(async ({ data }) => {
    const { sessionId } = data;
    const fs = await import("node:fs/promises");
    const sessionPath = `/home/team/shared/sessions/${sessionId}/session.json`;
    try {
      const raw = await fs.readFile(sessionPath, "utf8");
      const session = JSON.parse(raw);
      session.status = "hired";
      session.hiredAt = new Date().toISOString();
      await fs.writeFile(sessionPath, JSON.stringify(session, null, 2));
      return { success: true };
    } catch {
      return { success: false };
    }
  });

export const Route = createFileRoute("/checkout/")({
  component: Checkout,
});

const deliverables = [
  { icon: "🧹", title: "Deep Data Cleaning", desc: "Dedup, standardization, and reconciliation by the Auditor" },
  { icon: "📊", title: "Full Analysis", desc: "EDA, anomaly detection, and metrics by the Analyst" },
  { icon: "🔍", title: "Audit Trail", desc: "Every correction logged, timestamped, and explained" },
  { icon: "📋", title: "Decision Memo", desc: "Clear recommendations synthesized by the Manager" },
  { icon: "📑", title: "Excel Workbook", desc: "Cleaned data, analysis, and audit trail in one professional file" },
];

function Checkout() {
  const { sessionId } = Route.useParams();
  const [hiring, setHiring] = useState(false);

  const handleHire = async () => {
    setHiring(true);
    try {
      const result = await hireFirm({ data: sessionId });
      if (result.success) {
        const successUrl = `${window.location.origin}/results/${sessionId}`;
        window.location.href = `${STRIPE_LINK}?client_reference_id=${sessionId}&success_url=${encodeURIComponent(successUrl)}`;
      }
    } catch {
      setHiring(false);
    }
  };

  return (
    <div className="mx-auto max-w-2xl px-8 py-16">
      <div className="text-center">
        <span className="inline-block rounded-sm border border-navy-200 px-3 py-1 text-xs font-medium uppercase tracking-[0.15em] text-navy-500">
          Engagement
        </span>
        <h1 className="mt-4 font-serif text-3xl font-bold text-navy sm:text-4xl">
          Hire the Firm
        </h1>
        <p className="mt-2 text-navy-500">
          Your data has been profiled. Engage the full firm for a comprehensive analysis.
        </p>
      </div>

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
            $50 <span className="text-base font-normal text-navy-400">USD</span>
          </p>
          <p className="mt-1 text-xs text-navy-400">One-time payment. No recurring fees.</p>

          <button
            onClick={handleHire}
            disabled={hiring}
            className="mt-6 w-full rounded-sm bg-navy px-8 py-3.5 text-sm font-semibold uppercase tracking-wider text-white transition-colors hover:bg-navy-700 disabled:opacity-50 disabled:cursor-not-allowed"
          >
            {hiring ? (
              <span className="flex items-center justify-center gap-2">
                <span className="h-4 w-4 animate-spin rounded-full border-2 border-white border-t-transparent" />
                Processing
              </span>
            ) : (
              "Pay $50 & Engage the Firm"
            )}
          </button>
          <p className="mt-3 text-xs text-navy-400">
            Secure checkout via Stripe. You will be redirected to complete payment.
          </p>
        </div>
      </div>

      <div className="mt-8 text-center">
        <Link to={`/preview/${sessionId}`} className="text-xs text-navy-500 hover:text-navy underline">
          &larr; Return to data profile
        </Link>
      </div>
    </div>
  );
}