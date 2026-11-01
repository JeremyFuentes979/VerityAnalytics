import { createFileRoute } from "@tanstack/react-router";

const json = (body: unknown, status: number) =>
  new Response(JSON.stringify(body), { status, headers: { "Content-Type": "application/json" } });

export const Route = createFileRoute("/api/download/$sessionId")({
  server: {
    handlers: {
      GET: async ({ params }) => {
        const { isValidSessionId, getSessionDir } = await import("../../lib/sessionPaths");
        const { readSession } = await import("../../lib/sessions.server");
        const { sessionId } = params;
        if (!isValidSessionId(sessionId)) return json({ error: "Not found" }, 404);

        const session = await readSession(sessionId);
        if (!session) return json({ error: "Not found" }, 404);
        if (!session.paidAt) return json({ error: "Payment required" }, 402);
        if (session.status !== "complete") return json({ error: "Workbook not ready" }, 409);

        try {
          const { readFile } = await import("node:fs/promises");
          const file = await readFile(`${getSessionDir(sessionId)}/final_workbook.xlsx`);
          return new Response(file, {
            headers: {
              "Content-Type": "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
              "Content-Length": String(file.length),
              "Content-Disposition": `attachment; filename="verity-analytics-${sessionId.slice(0, 8)}.xlsx"`,
              "Cache-Control": "private, no-store",
            },
          });
        } catch {
          return json({ error: "Workbook not ready" }, 404);
        }
      },
    },
  },
});
