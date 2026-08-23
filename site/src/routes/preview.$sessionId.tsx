import { createFileRoute, Link } from "@tanstack/react-router";
import { createServerFn } from "@tanstack/react-start";

const getSession = createServerFn({ method: "GET" })
  .validator((d: unknown) => ({ sessionId: String(d) }))
  .handler(async ({ data }) => {
    const { sessionId } = data;
    const fs = await import("node:fs/promises");
    const path = `/home/team/shared/sessions/${sessionId}`;
    try {
      const session = JSON.parse(await fs.readFile(`${path}/session.json`, "utf8"));
      let profile = null;
      try { profile = JSON.parse(await fs.readFile(`${path}/profile.json`, "utf8")); } catch { /* */ }
      return { session, profile };
    } catch {
      return null;
    }
  });

export const Route = createFileRoute("/preview/$sessionId")({
  loader: async ({ params }) => getSession({ data: params.sessionId }),
  component: Preview,
});

function Preview() {
  const data = Route.useLoaderData();
  const { sessionId } = Route.useParams();

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

  return (
    <div className="mx-auto max-w-4xl px-8 py-16">
      <div className="text-center">
        <span className="inline-block rounded-sm border border-green-300 bg-green-50 px-3 py-1 text-xs font-medium uppercase tracking-[0.1em] text-green-700">
          Free Preview
        </span>
        <h1 className="mt-4 font-serif text-3xl font-bold text-navy sm:text-4xl">
          Data Profile
        </h1>
        <p className="mt-1 text-sm text-navy-500">
          {session.fileName} &middot; Submitted {new Date(session.createdAt).toLocaleString()}
        </p>
      </div>

      {profile ? (
        <div className="mt-10 space-y-8">
          <div className="rounded-sm border border-navy-100 p-6">
            <h2 className="text-sm font-bold uppercase tracking-wider text-navy">Schema Overview</h2>
            <div className="mt-4 grid grid-cols-3 gap-4 text-center">
              <div className="rounded-sm bg-navy-50 p-4">
                <p className="font-serif text-2xl font-bold text-navy">{profile.rowCount?.toLocaleString() || "—"}</p>
                <p className="text-xs text-navy-500">Rows</p>
              </div>
              <div className="rounded-sm bg-navy-50 p-4">
                <p className="font-serif text-2xl font-bold text-navy">{profile.columnCount || "—"}</p>
                <p className="text-xs text-navy-500">Columns</p>
              </div>
              <div className="rounded-sm bg-navy-50 p-4">
                <p className="font-serif text-2xl font-bold text-navy">{profile.fileSize || "—"}</p>
                <p className="text-xs text-navy-500">File Size</p>
              </div>
            </div>
          </div>

          {profile.columns && profile.columns.length > 0 && (
            <div className="rounded-sm border border-navy-100 p-6">
              <h2 className="text-sm font-bold uppercase tracking-wider text-navy">Columns</h2>
              <div className="mt-4 overflow-x-auto">
                <table className="w-full text-left text-sm">
                  <thead>
                    <tr className="border-b border-navy-100">
                      <th className="pb-2 pr-4 text-xs font-medium uppercase tracking-wider text-navy-400">Field</th>
                      <th className="pb-2 pr-4 text-xs font-medium uppercase tracking-wider text-navy-400">Type</th>
                      <th className="pb-2 pr-4 text-xs font-medium uppercase tracking-wider text-navy-400">Null %</th>
                      <th className="pb-2 text-xs font-medium uppercase tracking-wider text-navy-400">Unique</th>
                    </tr>
                  </thead>
                  <tbody>
                    {(profile.columns as Array<{name: string; type: string; nullPct: number; unique: number}>).map((col, i) => (
                      <tr key={i} className="border-b border-navy-50">
                        <td className="py-2 pr-4 font-medium text-navy">{col.name}</td>
                        <td className="py-2 pr-4 text-navy-500">{col.type}</td>
                        <td className="py-2 pr-4 text-navy-500">{(col.nullPct * 100).toFixed(1)}%</td>
                        <td className="py-2 text-navy-500">{col.unique}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </div>
          )}

          {profile.warnings && profile.warnings.length > 0 && (
            <div className="rounded-sm border border-amber-200 bg-amber-50 p-6">
              <h2 className="text-sm font-bold uppercase tracking-wider text-amber-700">Items Noted</h2>
              <ul className="mt-3 space-y-1 text-sm text-amber-700">
                {(profile.warnings as string[]).map((w, i) => (
                  <li key={i} className="flex items-start gap-2">
                    <span className="mt-0.5">—</span>
                    <span>{w}</span>
                  </li>
                ))}
              </ul>
            </div>
          )}

          <div className="rounded-sm bg-navy p-8 text-center text-white">
            <h2 className="font-serif text-2xl font-bold">Engage the Full Firm</h2>
            <p className="mt-2 text-sm text-navy-200">
              For $50, our full team produces cleaned data, deep analysis, a complete audit trail, and a professional Excel workbook.
            </p>
            <Link
              to={`/checkout/${sessionId}`}
              className="mt-6 inline-block rounded-sm bg-gold px-8 py-3 text-sm font-semibold uppercase tracking-wider text-navy transition-colors hover:bg-gold-600"
            >
              Hire Quorum — $50
            </Link>
          </div>
        </div>
      ) : (
        <div className="mt-16 text-center">
          <div className="inline-block rounded-sm border border-navy-100 p-10">
            <div className="mx-auto h-6 w-6 animate-spin rounded-full border-2 border-navy border-t-transparent" />
            <p className="mt-4 font-medium text-navy">Profiling your data...</p>
            <p className="mt-1 text-sm text-navy-400">This typically completes within a few seconds. Refresh the page to check.</p>
          </div>
        </div>
      )}
    </div>
  );
}