import { createFileRoute, Link } from "@tanstack/react-router";
import { createServerFn } from "@tanstack/react-start";
import { useEffect, useState } from "react";

const getStatus = createServerFn({ method: "GET" })
  .validator((d: unknown) => ({ sessionId: String(d) }))
  .handler(async ({ data }) => {
    const { sessionId } = data;
    const fs = await import("node:fs/promises");
    const basePath = `/home/team/shared/sessions/${sessionId}`;
    try {
      const session = JSON.parse(await fs.readFile(`${basePath}/session.json`, "utf8"));
      const artifacts = { profile: false, analysis: false, auditTrail: false, decisionMemo: false, workbook: false };
      for (const key of Object.keys(artifacts)) {
        const fileName = key === "workbook" ? "final_workbook.xlsx" : `${key}.json`;
        try { await fs.access(`${basePath}/${fileName}`); (artifacts as Record<string, boolean>)[key] = true; } catch { /* */ }
      }
      return { session, artifacts, exists: true };
    } catch {
      return { exists: false };
    }
  });

const triggerWorkflow = createServerFn({ method: "POST" })
  .validator((d: unknown) => ({ sessionId: String(d) }))
  .handler(async ({ data }) => {
    const { sessionId } = data;
    const { execSync } = await import("node:child_process");
    execSync(`nohup python3 /home/team/shared/workflow/orchestrator.py ${sessionId} > /tmp/quorum-workflow-${sessionId}.log 2>&1 &`, { timeout: 5000 });
    return { started: true };
  });

export const Route = createFileRoute("/results/$sessionId")({
  loader: async ({ params }) => getStatus({ data: params.sessionId }),
  component: Results,
  staleTime: 5_000,
});

const stages = [
  { key: "profile" as const, label: "Researcher — Data Profiling", icon: "📋" },
  { key: "analysis" as const, label: "Analyst — Pattern Analysis", icon: "📊" },
  { key: "auditTrail" as const, label: "Auditor — Validation & Cleaning", icon: "✅" },
  { key: "decisionMemo" as const, label: "Manager — Synthesis & Decision Memo", icon: "📋" },
  { key: "workbook" as const, label: "Manager — Excel Workbook", icon: "📑" },
];

function Results() {
  const data = Route.useLoaderData();
  const { sessionId } = Route.useParams();
  const [workflowStarted, setWorkflowStarted] = useState(false);

  useEffect(() => {
    if (data?.exists && data.session.status === "hired" && !workflowStarted) {
      setWorkflowStarted(true);
      triggerWorkflow({ data: sessionId }).catch(() => {});
    }
  }, [data, sessionId, workflowStarted]);

  if (!data?.exists) {
    return (
      <div className="mx-auto max-w-2xl px-8 py-24 text-center">
        <p className="font-serif text-2xl font-bold text-navy">Engagement Not Found</p>
        <Link to="/upload" className="mt-6 inline-block rounded-sm bg-navy px-6 py-2.5 text-sm font-medium text-white hover:bg-navy-700">
          Submit New Data
        </Link>
      </div>
    );
  }

  const { session, artifacts } = data;
  const allComplete = artifacts.workbook && artifacts.decisionMemo;

  return (
    <div className="mx-auto max-w-4xl px-8 py-16">
      <div className="text-center">
        <span className={`inline-block rounded-sm border px-3 py-1 text-xs font-medium uppercase tracking-[0.1em] ${
          allComplete ? "border-green-300 bg-green-50 text-green-700" : "border-gold/30 bg-gold-50 text-gold-700"
        }`}>
          {allComplete ? "Analysis Complete" : "Analysis in Progress"}
        </span>
        <h1 className="mt-4 font-serif text-3xl font-bold text-navy sm:text-4xl">
          {allComplete ? "Engagement Complete" : "The Firm Is Working"}
        </h1>
        <p className="mt-1 text-sm text-navy-500">{session.fileName}</p>
        {!allComplete && (
          <p className="mt-2 text-xs text-navy-400">This page refreshes automatically. No need to reload.</p>
        )}
      </div>

      {/* Pipeline */}
      <div className="mt-10 space-y-3">
        {stages.map((stage) => {
          const done = artifacts[stage.key];
          return (
            <div
              key={stage.key}
              className={`flex items-center gap-4 rounded-sm border p-4 ${
                done ? "border-green-200 bg-green-50" : "border-navy-100 bg-white"
              }`}
            >
              <span className={`text-lg ${done ? "" : "text-navy-300"}`}>{done ? "✓" : stage.icon}</span>
              <span className={`flex-1 text-sm ${done ? "font-medium text-green-800" : "text-navy-500"}`}>
                {stage.label}
              </span>
              {done && <span className="text-xs font-medium text-green-600">Complete</span>}
            </div>
          );
        })}
      </div>

      {allComplete && (
        <div className="mt-10 rounded-sm bg-navy p-8 text-center text-white">
          <h2 className="font-serif text-2xl font-bold">Your Workbook Is Ready</h2>
          <p className="mt-2 text-sm text-navy-200">
            Cleaned data, analysis results, audit trail, and decision memo — all in one file.
          </p>
          <a
            href={`/api/download/${sessionId}`}
            className="mt-6 inline-block rounded-sm bg-gold px-8 py-3 text-sm font-semibold uppercase tracking-wider text-navy transition-colors hover:bg-gold-600"
          >
            Download Workbook (.xlsx)
          </a>
        </div>
      )}

      <div className="mt-10 border-t border-navy-100 pt-10 text-center">
        <Link to="/upload" className="text-sm text-navy-500 hover:text-navy underline">
          Analyze another dataset
        </Link>
      </div>
    </div>
  );
}