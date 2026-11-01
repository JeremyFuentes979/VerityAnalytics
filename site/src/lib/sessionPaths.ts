import { resolve } from "node:path";

// Session ids are crypto.randomUUID() values. Anything else is rejected before it
// can reach the filesystem or a child process, which rules out path traversal and
// shell injection through the id.
const UUID_RE = /^[0-9a-f]{8}-[0-9a-f]{4}-[1-8][0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$/i;

export function isValidSessionId(id: unknown): id is string {
  return typeof id === "string" && UUID_RE.test(id);
}

export function getRepoRoot() {
  return process.env.VERITY_REPO_ROOT || resolve(process.cwd(), "..");
}

export function getSessionsDir() {
  return process.env.VERITY_SESSIONS_DIR || resolve(getRepoRoot(), "sessions");
}

export function getSessionDir(sessionId: string) {
  if (!isValidSessionId(sessionId)) throw new Error("Invalid session id");
  return resolve(getSessionsDir(), sessionId);
}
