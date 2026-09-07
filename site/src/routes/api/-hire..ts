// API route to trigger the full Quorum workflow for a session
// Called after payment is confirmed.
import { createAPIFileRoute } from "@tanstack/react-start/api";
import { execSync } from "node:child_process";
import { getSessionDir } from "../../lib/sessionPaths";

export const APIRoute = createAPIFileRoute("/api/hire/$sessionId")({
  POST: async ({ params }) => {
    const { sessionId } = params;
    const sessionDir = getSessionDir(sessionId);

    // Verify session exists
    const fs = await import("node:fs/promises");
    try {
      await fs.access(`${sessionDir}/session.json`);
    } catch {
      return new Response(JSON.stringify({ error: "Session not found" }), {
        status: 404,
        headers: { "Content-Type": "application/json" },
      });
    }

    // Run the workflow orchestrator in background (non-blocking)
    const repoRoot = process.env.QUORUM_REPO_ROOT || "..";
    execSync(
      `nohup python3 "${repoRoot}/workflow/orchestrator.py" ${sessionId} > /tmp/quorum-workflow-${sessionId}.log 2>&1 &`,
      { timeout: 5000, cwd: repoRoot }
    );

    return new Response(
      JSON.stringify({
        sessionId,
        status: "started",
        message: "The firm has been hired. Workflow is running.",
      }),
      {
        headers: { "Content-Type": "application/json" },
      }
    );
  },
});