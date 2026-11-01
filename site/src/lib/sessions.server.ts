import { randomBytes } from "node:crypto";
import { access, mkdir, readFile, rename, writeFile } from "node:fs/promises";
import { basename } from "node:path";

import { getSessionDir, isValidSessionId } from "./sessionPaths";

export type SessionRecord = {
  sessionId: string;
  fileName: string;
  fileSize?: number;
  status: string;
  detail?: string;
  createdAt: string;
  updatedAt?: string;
  paidAt?: string;
  stripeCheckoutSessionId?: string;
  amountPaid?: number;
  [key: string]: unknown;
};

/** What the browser is allowed to know about a session. */
export type PublicSession = {
  sessionId: string;
  fileName: string;
  fileSize: number | null;
  status: string;
  detail: string | null;
  createdAt: string;
  paid: boolean;
};

export async function readSession(sessionId: string): Promise<SessionRecord | null> {
  if (!isValidSessionId(sessionId)) return null;
  try {
    return JSON.parse(await readFile(`${getSessionDir(sessionId)}/session.json`, "utf8"));
  } catch {
    return null;
  }
}

/** Write via temp file + rename so the Python workflow never reads a half-written file. */
export async function writeSession(session: SessionRecord): Promise<void> {
  const dir = getSessionDir(session.sessionId);
  const tmp = `${dir}/.session-${randomBytes(6).toString("hex")}.json`;
  await writeFile(tmp, JSON.stringify(session, null, 2));
  await rename(tmp, `${dir}/session.json`);
}

export async function readArtifactJson(sessionId: string, name: string): Promise<unknown | null> {
  try {
    return JSON.parse(await readFile(`${getSessionDir(sessionId)}/${name}`, "utf8"));
  } catch {
    return null;
  }
}

export async function fileExists(path: string): Promise<boolean> {
  try {
    await access(path);
    return true;
  } catch {
    return false;
  }
}

export function toPublic(session: SessionRecord): PublicSession {
  return {
    sessionId: session.sessionId,
    fileName: session.fileName,
    fileSize: typeof session.fileSize === "number" ? session.fileSize : null,
    status: session.status,
    detail: session.detail ?? null,
    createdAt: session.createdAt,
    paid: Boolean(session.paidAt),
  };
}

/** Keep only a safe display name: no paths, no control characters, bounded length. */
export function sanitizeFileName(name: string): string {
  const base = basename(name.replace(/\\/g, "/"))
    // eslint-disable-next-line no-control-regex
    .replace(/[\u0000-\u001f\u007f<>:"|?*]/g, "")
    .trim();
  return (base || "upload").slice(0, 120);
}

export async function createSessionDir(sessionId: string): Promise<string> {
  const dir = getSessionDir(sessionId);
  await mkdir(dir, { recursive: true });
  return dir;
}

export const WORKFLOW_RUNNING = new Set([
  "queued",
  "running_researcher",
  "running_analyst",
  "running_auditor",
  "running_manager",
]);
