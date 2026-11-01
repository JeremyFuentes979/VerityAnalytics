import { createFileRoute, Link, useRouter } from "@tanstack/react-router";
import { createServerFn } from "@tanstack/react-start";
import { useEffect } from "react";

import { PRICE_DISPLAY } from "../lib/config";
import type { PublicSession } from "../lib/sessions.server";

type ColumnStats = { dtype: string; null_percentage: number; unique_count: number };
type Profile = {
  row_count: number;
  column_count: number;
  columns: Record<string, ColumnStats>;
  warnings?: string[];
  file_size_bytes?: number;
};

const getPreview = createServerFn({ method: "GET" })
  .validator((d: { sessionId: string }) => ({ sessionId: String(d.sessionId) }))
  .handler(async ({ data }) => {
    const { readSession, readArtifactJson, toPublic } = await import("../lib/sessions.server");
    const session = await readSession(data.sessionId);
    if (!session) return null;
    const profile = (await readArtifactJson(data.sessionId, "profile.json")) as Profile | null;
    return { session: toPublic(session) as PublicSession, profile };
  });

export const Route = createFileRoute("/preview/$sessionId")({
  loader: ({ params }) => getPreview({ data: { sessionId: params.sessionId } }),
  component: Preview,
});

function formatBytes(n: number | null | undefined) {
  if (!n) return "—";
  if (n < 1024) return `${n} B`;
  if (n < 1024 * 1024) return `${(n / 1024).toFixed(1)} KB`;
  return `${(n / 1024 / 1024).toFixed(1)} MB`;
}

function Shell({ children }: { children: React.ReactNode }) {
  return <div className="mx-auto max-w-4xl px-8 py-16">{children}</div>;
}

function Preview() {
  const data = Route.useLoaderData();
  const router = useRouter();
  const status = data?.session.status;
  const inProgress = status === "uploaded" || status === "profiling";

  // Re-check every couple of seconds until profiling finishes.
  useEffect(() => {
    if (!inProgress) return;
    const timer = setInterval(() => router.invalidate(), 2000);
    return () => clearInterval(timer);
  }, [inProgress, router]);

  if (!data) {
    return (
      <div className="mx-auto max-w-2xl px-8 py-24 text-center">
        <p className="font-serif text-2xl font-bold text-navy">Engagement Not Found</p>
        <p className="mt-2 text-sm text-navy-500">This session does not exist or has expired.</p>
        <Link to="/upload" className="mt-6 inline-block rounded-sm bg-navy px-6 py-2.5 text-sm font-medium text-white hover:bg-navy-700">
          Submit New Data
        </Link>
      </div>
    );
  }

  const { session, profile } = data;

  if (status === "profile_error") {
    return (
      <div className="mx-auto max-w-2xl px-8 py-24 text-center">
        <p className="font-serif text-2xl font-bold text-navy">We couldn&rsquo;t read that file</p>
        <p className="mt-3 rounded-sm border border-red-200 bg-red-50 p-4 text-sm text-red-700">
          {session.detail ?? "The file could not be read."}
        </p>
        <Link to="/upload" className="mt-6 inline-block rounded-sm bg-navy px-6 py-2.5 text-sm font-medium text-white hover:bg-navy-700">
          Try Another File
        </Link>
      </div>
    );
  }

  if (!profile) {
    return (
      <Shell>
        <div className="mt-8 text-center">
          <div className="inline-block rounded-sm border border-navy-100 p-10">
            <div className="mx-auto h-6 w-6 animate-spin rounded-full border-2 border-navy border-t-transparent" />
            <p className="mt-4 font-medium text-navy">Profiling your data&hellip;</p>
            <p className="mt-1 text-sm text-navy-500">This usually takes a few seconds. This page updates automatically.</p>
          </div>
        </div>
      </Shell>
    );
  }

  const columns = Object.entries(profile.columns ?? {});

  return (
    <Shell>
      <div className="text-center">
        <span className="inline-block rounded-sm border border-green-300 bg-green-50 px-3 py-1 text-xs font-medium uppercase tracking-[0.1em] text-green-700">
          Free Preview
        </span>
        <h1 className="mt-4 font-serif text-3xl font-bold text-navy sm:text-4xl">Data Profile</h1>
        <p className="mt-1 text-sm text-navy-500">
          {session.fileName} &middot; Submitted {new Date(session.createdAt).toLocaleString()}
        </p>
      </div>

      <div className="mt-10 space-y-8">
        <div className="rounded-sm border border-navy-100 p-6">
          <h2 className="text-sm font-bold uppercase tracking-wider text-navy">Schema Overview</h2>
          <div className="mt-4 grid grid-cols-3 gap-4 text-center">
            <div className="rounded-sm bg-navy-50 p-4">
              <p className="font-serif text-2xl font-bold text-navy">{profile.row_count.toLocaleString()}</p>
              <p className="text-xs text-navy-500">Rows</p>
            </div>
            <div className="rounded-sm bg-navy-50 p-4">
              <p className="font-serif text-2xl font-bold text-navy">{profile.column_count.toLocaleString()}</p>
              <p className="text-xs text-navy-500">Columns</p>
            </div>
            <div className="rounded-sm bg-navy-50 p-4">
              <p className="font-serif text-2xl font-bold text-navy">{formatBytes(session.fileSize ?? profile.file_size_bytes)}</p>
              <p className="text-xs text-navy-500">File Size</p>
            </div>
          </div>
        </div>

        {columns.length > 0 && (
          <div className="rounded-sm border border-navy-100 p-6">
            <h2 className="text-sm font-bold uppercase tracking-wider text-navy">Columns</h2>
            <div className="mt-4 overflow-x-auto">
              <table className="w-full text-left text-sm">
                <thead>
                  <tr className="border-b border-navy-100">
                    <th className="pb-2 pr-4 text-xs font-medium uppercase tracking-wider text-navy-500">Field</th>
                    <th className="pb-2 pr-4 text-xs font-medium uppercase tracking-wider text-navy-500">Type</th>
                    <th className="pb-2 pr-4 text-xs font-medium uppercase tracking-wider text-navy-500">Missing</th>
                    <th className="pb-2 text-xs font-medium uppercase tracking-wider text-navy-500">Unique</th>
                  </tr>
                </thead>
                <tbody>
                  {columns.slice(0, 200).map(([name, col]) => (
                    <tr key={name} className="border-b border-navy-50">
                      <td className="py-2 pr-4 font-medium text-navy">{name}</td>
                      <td className="py-2 pr-4 text-navy-600">{col.dtype}</td>
                      <td className="py-2 pr-4 text-navy-600">{col.null_percentage.toFixed(1)}%</td>
                      <td className="py-2 text-navy-600">{col.unique_count.toLocaleString()}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
              {columns.length > 200 && <p className="mt-2 text-xs text-navy-500">Showing the first 200 of {columns.length} columns.</p>}
            </div>
          </div>
        )}

        {profile.warnings && profile.warnings.length > 0 && (
          <div className="rounded-sm border border-amber-200 bg-amber-50 p-6">
            <h2 className="text-sm font-bold uppercase tracking-wider text-amber-800">Items Noted</h2>
            <ul className="mt-3 space-y-1 text-sm text-amber-800">
              {profile.warnings.map((w, i) => (
                <li key={i} className="flex items-start gap-2">
                  <span className="mt-0.5">&mdash;</span>
                  <span>{w}</span>
                </li>
              ))}
            </ul>
          </div>
        )}

        <div className="rounded-sm bg-navy p-8 text-center text-white">
          {session.paid ? (
            <>
              <h2 className="font-serif text-2xl font-bold">Your engagement is under way</h2>
              <Link
                to="/results/$sessionId"
                params={{ sessionId: session.sessionId }}
                className="mt-6 inline-block rounded-sm bg-gold px-8 py-3 text-sm font-semibold uppercase tracking-wider text-navy transition-colors hover:bg-gold-600"
              >
                View Progress
              </Link>
            </>
          ) : (
            <>
              <h2 className="font-serif text-2xl font-bold">Engage the Full Firm</h2>
              <p className="mt-2 text-sm text-navy-200">
                For {PRICE_DISPLAY}, our full team produces cleaned data, deep analysis, a complete audit trail, and a professional Excel workbook.
              </p>
              <Link
                to="/checkout/$sessionId"
                params={{ sessionId: session.sessionId }}
                className="mt-6 inline-block rounded-sm bg-gold px-8 py-3 text-sm font-semibold uppercase tracking-wider text-navy transition-colors hover:bg-gold-600"
              >
                Hire Verity Analytics &mdash; {PRICE_DISPLAY}
              </Link>
            </>
          )}
        </div>
      </div>
    </Shell>
  );
}
