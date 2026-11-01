import { spawn } from "node:child_process";
import { closeSync, existsSync, openSync } from "node:fs";
import { resolve } from "node:path";

import { getRepoRoot, getSessionDir, isValidSessionId } from "./sessionPaths";

function pythonExecutable(): string {
  if (process.env.VERITY_PYTHON) return process.env.VERITY_PYTHON;
  const venv = resolve(getRepoRoot(), ".venv", "bin", "python");
  return existsSync(venv) ? venv : "python3";
}

/**
 * Start the Python orchestrator detached from the web server.
 * Arguments are passed as an argv array (never through a shell) and the id is
 * validated first, so a hostile id can't turn into a command.
 */
export function startWorkflow(sessionId: string, stage: "profile" | "full"): void {
  if (!isValidSessionId(sessionId)) throw new Error("Invalid session id");

  const repoRoot = getRepoRoot();
  const script = resolve(repoRoot, "workflow", "orchestrator.py");
  const logFd = openSync(`${getSessionDir(sessionId)}/workflow.log`, "a");
  try {
    const child = spawn(pythonExecutable(), [script, sessionId, "--stage", stage], {
      cwd: repoRoot,
      detached: true,
      stdio: ["ignore", logFd, logFd],
      env: { ...process.env, VERITY_SESSIONS_DIR: resolve(getSessionDir(sessionId), "..") },
    });
    child.on("error", (err) => console.error(`[workflow] failed to start for ${sessionId}:`, err));
    child.unref();
  } finally {
    closeSync(logFd);
  }
}
