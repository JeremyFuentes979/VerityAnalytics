// Download the final Excel workbook for a given session
// This is a TanStack Start API route, not a page.
import { createAPIFileRoute } from "@tanstack/react-start/api";

export const APIRoute = createAPIFileRoute("/api/download/$sessionId")({
  GET: async ({ params }) => {
    const { sessionId } = params;
    const path = `/home/team/shared/sessions/${sessionId}/final_workbook.xlsx`;

    try {
      const fs = await import("node:fs/promises");
      await fs.access(path);
      const file = await fs.readFile(path);

      return new Response(file, {
        headers: {
          "Content-Type": "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
          "Content-Disposition": `attachment; filename="quorum-analysis-${sessionId.slice(0, 8)}.xlsx"`,
        },
      });
    } catch {
      return new Response(JSON.stringify({ error: "Workbook not ready" }), {
        status: 404,
        headers: { "Content-Type": "application/json" },
      });
    }
  },
});