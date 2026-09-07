import { resolve } from "node:path";

export function getRepoRoot() {
  return process.env.QUORUM_REPO_ROOT || resolve(process.cwd(), "..");
}

export function getSessionsDir() {
  return process.env.QUORUM_SESSIONS_DIR || resolve(getRepoRoot(), "sessions");
}

export function getSessionDir(sessionId: string) {
  return resolve(getSessionsDir(), sessionId);
}
