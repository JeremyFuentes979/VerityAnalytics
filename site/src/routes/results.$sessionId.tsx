import { createFileRoute, Link, useNavigate, useRouter } from "@tanstack/react-router";
import { createServerFn } from "@tanstack/react-start";
import { useEffect, useState } from "react";

import type { PublicSession } from "../lib/sessions.server";

type Artifacts = { profile: boolean; analysis: boolean; auditTrail: boolean; decisionMemo: boolean; workbook: boolean };

const getResults = createServerFn({ method: "GET" })
  .inputValidator((d: { sessionId: string; cs?: string }) => ({ sessionId: String(d.sessionId), cs: d.cs ? String(d.cs) : undefined }))
  .handler(async ({ data }) => {
    const { readSession, toPublic, fileExists } = await import("../lib/sessions.server");
    const { getSessionDir } = await import("../lib/sessionPaths");

    let session = await readSession(data.sessionId);
    if (!session) return { exists: false as const };

    let paymentNotice: string | null = null;
    if (data.cs && !session.paidAt) {
      // Returning from Stripe: verify the payment with Stripe before unlocking anything.
      try {
        const { confirmCheckout } = await import("../lib/payments.server");
        await confirmCheckout(data.sessionId, data.cs);
        session = (await readSession(data.sessionId)) ?? session;
      } catch (err) {
        console.error("[results] payment confirmation failed:", err);
        paymentNotice = "We couldn't confirm your payment yet. If you were charged, this page will update within a minute.";
      }
    }

    const dir = getSessionDir(data.sessionId);
    const artifacts: Artifacts = {
      profile: await fileExists(`${dir}/profile.json`),
      analysis: await fileExists(`${dir}/analysis.json`),
      auditTrail: await fileExists(`${dir}/audit_trail.json`),
      decisionMemo: await fileExists(`${dir}/decision_memo.json`),
      workbook: session.status === "complete" && (await fileExists(`${dir}/final_workbook.xlsx`)),
    };
    return { exists: true as const, session: toPublic(session) as PublicSession, artifacts, paymentNotice };
  });

const retryWorkflow = createServerFn({ method: "POST" })
  .inputValidator((d: { sessionId: string }) => ({ sessionId: String(d.sessionId) }))
  .handler(async ({ data }) => {
    const { readSession, writeSession } = await import("../lib/sessions.server");
    const { startWorkflow } = await import("../lib/workflow.server");
    const session = await readSession(data.sessionId);
    // Only a paid session whose workflow failed may be retried.
    if (!session?.paidAt || session.status !== "error") return { started: false };
    session.status = "paid";
    session.detail = "Retrying";
    await writeSession(session);
    startWorkflow(data.sessionId, "full");
    return { started: true };
  });

export const Route = createFileRoute("/results/$sessionId")({
  validateSearch: (search: Record<string, unknown>): { cs?: string } =>
    typeof search.cs === "string" && search.cs ? { cs: search.cs } : {},
  loaderDeps: ({ search }) => ({ cs: search.cs }),
  loader: ({ params, deps }) => getResults({ data: { sessionId: params.sessionId, cs: deps.cs } }),
  component: Results,
});

const stages = [
  { key: "profile" as const, label: "Researcher — Data Profiling", icon: "📋" },
  { key: "analysis" as const, label: "Analyst — Pattern Analysis", icon: "📊" },
  { key: "auditTrail" as const, label: "Auditor — Validation & Cleaning", icon: "✅" },
  { key: "decisionMemo" as const, label: "Manager — Synthesis & Decision Memo", icon: "📝" },
  { key: "workbook" as const, label: "Manager — Excel Workbook", icon: "📑" },
];

function Results() {
  const data = Route.useLoaderData();
  const { sessionId } = Route.useParams();
  const { cs } = Route.useSearch();
  const router = useRouter();
  const navigate = useNavigate();
  const [retrying, setRetrying] = useState(false);

  const status = data.exists ? data.session.status : "";
  const paid = data.exists && data.session.paid;
  const terminal = status === "complete" || status === "error" || !data.exists;
  // Poll while a payment is being confirmed or the workflow is running.
  const shouldPoll = data.exists && !terminal && (paid || Boolean(cs));

  useEffect(() => {
    if (!shouldPoll) return;
    const timer = setInterval(() => router.invalidate(), 2500);
    return () => clearInterval(timer);
  }, [shouldPoll, router]);

  // Once the payment is confirmed, drop the Stripe id from the URL.
  useEffect(() => {
    if (cs && paid) navigate({ to: "/results/$sessionId", params: { sessionId }, search: {}, replace: true });
  }, [cs, paid, navigate, sessionId]);

  if (!data.exists) {
    return (
      <div className="mx-auto max-w-2xl px-8 py-24 text-center">
        <p className="font-serif text-2xl font-bold text-navy">Engagement Not Found</p>
        <Link to="/upload" className="mt-6 inline-block rounded-sm bg-navy px-6 py-2.5 text-sm font-medium text-white hover:bg-navy-700">
          Submit New Data
        </Link>
      </div>
    );
  }

  const { session, artifacts, paymentNotice } = data;

  if (!session.paid) {
    return (
      <div className="mx-auto max-w-2xl px-8 py-24 text-center">
        {cs ? (
          <>
            <div className="mx-auto h-6 w-6 animate-spin rounded-full border-2 border-navy border-t-transparent" />
            <p className="mt-4 font-serif text-2xl font-bold text-navy">Confirming your payment&hellip;</p>
          </>
        ) : (
          <p className="font-serif text-2xl font-bold text-navy">Payment required</p>
        )}
        {paymentNotice && <p className="mt-3 text-sm text-amber-800">{paymentNotice}</p>}
        <Link
          to="/checkout/$sessionId"
          params={{ sessionId }}
          className="mt-6 inline-block rounded-sm bg-navy px-6 py-2.5 text-sm font-medium text-white hover:bg-navy-700"
        >
          Go to checkout
        </Link>
      </div>
    );
  }

  const allComplete = status === "complete";
  const failed = status === "error";

  const handleRetry = async () => {
    setRetrying(true);
    try {
      await retryWorkflow({ data: { sessionId } });
      await router.invalidate();
    } finally {
      setRetrying(false);
    }
  };

  return (
    <div className="mx-auto max-w-4xl px-8 py-16">
      <div className="text-center">
        <span
          className={`inline-block rounded-sm border px-3 py-1 text-xs font-medium uppercase tracking-[0.1em] ${
            allComplete
              ? "border-green-300 bg-green-50 text-green-700"
              : failed
                ? "border-red-300 bg-red-50 text-red-700"
                : "border-gold/30 bg-gold-50 text-gold-700"
          }`}
        >
          {allComplete ? "Analysis Complete" : failed ? "Needs Attention" : "Analysis in Progress"}
        </span>
        <h1 className="mt-4 font-serif text-3xl font-bold text-navy sm:text-4xl">
          {allComplete ? "Engagement Complete" : failed ? "Something Went Wrong" : "The Firm Is Working"}
        </h1>
        <p className="mt-1 text-sm text-navy-500">{session.fileName}</p>
        {!allComplete && !failed && (
          <p className="mt-2 text-xs text-navy-500">This page refreshes automatically. No need to reload.</p>
        )}
      </div>

      <div className="mt-10 space-y-3">
        {stages.map((stage) => {
          const done = artifacts[stage.key];
          return (
            <div
              key={stage.key}
              className={`flex items-center gap-4 rounded-sm border p-4 ${done ? "border-green-200 bg-green-50" : "border-navy-100 bg-white"}`}
            >
              <span className={`text-lg ${done ? "" : "text-navy-300"}`}>{done ? "✓" : stage.icon}</span>
              <span className={`flex-1 text-sm ${done ? "font-medium text-green-800" : "text-navy-600"}`}>{stage.label}</span>
              {done && <span className="text-xs font-medium text-green-700">Complete</span>}
            </div>
          );
        })}
      </div>

      {failed && (
        <div className="mt-10 rounded-sm border border-red-200 bg-red-50 p-8 text-center">
          <p className="font-medium text-red-800">The workflow stopped before finishing.</p>
          {session.detail && <p className="mt-1 text-sm text-red-700">{session.detail}</p>}
          <p className="mt-2 text-sm text-red-700">Your payment is safe and you won&rsquo;t be charged again.</p>
          <button
            onClick={handleRetry}
            disabled={retrying}
            className="mt-5 rounded-sm bg-navy px-6 py-2.5 text-sm font-medium text-white hover:bg-navy-700 disabled:opacity-50"
          >
            {retrying ? "Restarting…" : "Try Again"}
          </button>
        </div>
      )}

      {allComplete && (
        <div className="mt-10 rounded-sm bg-navy p-8 text-center text-white">
          <h2 className="font-serif text-2xl font-bold">Your Workbook Is Ready</h2>
          <p className="mt-2 text-sm text-navy-200">Cleaned data, analysis results, audit trail, and decision memo — all in one file.</p>
          <a
            href={`/api/download/${sessionId}`}
            className="mt-6 inline-block rounded-sm bg-gold px-8 py-3 text-sm font-semibold uppercase tracking-wider text-navy transition-colors hover:bg-gold-600"
          >
            Download Workbook (.xlsx)
          </a>
          <p className="mt-4 text-xs text-navy-300">
            Bookmark this page to download again. Results are automated and should be reviewed by a qualified professional before material use.
          </p>
        </div>
      )}

      <div className="mt-10 border-t border-navy-100 pt-10 text-center">
        <Link to="/upload" className="text-sm text-navy-500 underline hover:text-navy">
          Analyze another dataset
        </Link>
      </div>
    </div>
  );
}
