import { createFileRoute } from "@tanstack/react-router";

import { ALLOWED_EXTENSIONS, MAX_UPLOAD_BYTES, type AllowedExtension } from "../../lib/config";

const json = (body: unknown, status = 200) =>
  new Response(JSON.stringify(body), { status, headers: { "Content-Type": "application/json" } });

// Free previews cost compute, so cap how many a single address can start per hour.
const WINDOW_MS = 60 * 60 * 1000;
const MAX_UPLOADS_PER_WINDOW = 30;
const hits = new Map<string, number[]>();

function rateLimited(ip: string): boolean {
  const now = Date.now();
  const recent = (hits.get(ip) ?? []).filter((t) => now - t < WINDOW_MS);
  if (recent.length >= MAX_UPLOADS_PER_WINDOW) {
    hits.set(ip, recent);
    return true;
  }
  recent.push(now);
  hits.set(ip, recent);
  if (hits.size > 5000) for (const [key, times] of hits) if (!times.some((t) => now - t < WINDOW_MS)) hits.delete(key);
  return false;
}

function startsWith(bytes: Uint8Array, signature: number[]) {
  return signature.every((b, i) => bytes[i] === b);
}

/** Cheap content check so a renamed random file fails now, not after a confusing profiling error. */
function looksLike(ext: AllowedExtension, bytes: Uint8Array): boolean {
  switch (ext) {
    case "pdf":
      return startsWith(bytes, [0x25, 0x50, 0x44, 0x46]); // %PDF
    case "xlsx":
      return startsWith(bytes, [0x50, 0x4b]); // zip container
    case "xls":
      return startsWith(bytes, [0xd0, 0xcf, 0x11, 0xe0]) || startsWith(bytes, [0x50, 0x4b]);
    case "csv":
      return !bytes.subarray(0, 8192).includes(0); // text files have no NUL bytes
  }
}

export const Route = createFileRoute("/api/upload")({
  server: {
    handlers: {
      POST: async ({ request }) => {
        const ip = request.headers.get("x-forwarded-for")?.split(",")[0]?.trim() || "local";
        if (rateLimited(ip)) return json({ error: "Too many uploads. Please try again later." }, 429);

        const declared = Number(request.headers.get("content-length") ?? 0);
        if (declared > MAX_UPLOAD_BYTES + 1024 * 1024) {
          return json({ error: "That file is larger than the 50 MB limit." }, 413);
        }

        let form: FormData;
        try {
          form = await request.formData();
        } catch {
          return json({ error: "The upload could not be read. Please try again." }, 400);
        }

        const file = form.get("file");
        if (!(file instanceof File)) return json({ error: "No file was provided." }, 400);
        if (file.size === 0) return json({ error: "That file is empty." }, 400);
        if (file.size > MAX_UPLOAD_BYTES) return json({ error: "That file is larger than the 50 MB limit." }, 413);

        const ext = file.name.split(".").pop()?.toLowerCase() as AllowedExtension | undefined;
        if (!ext || !(ALLOWED_EXTENSIONS as readonly string[]).includes(ext)) {
          return json({ error: "Accepted formats: .csv, .xlsx, .xls, .pdf" }, 400);
        }

        const bytes = new Uint8Array(await file.arrayBuffer());
        if (!looksLike(ext, bytes)) {
          return json({ error: `That file doesn't look like a valid .${ext} file.` }, 400);
        }

        const { createSessionDir, sanitizeFileName, writeSession } = await import("../../lib/sessions.server");
        const { startWorkflow } = await import("../../lib/workflow.server");
        const sessionId = crypto.randomUUID();
        const dir = await createSessionDir(sessionId);

        const { writeFile } = await import("node:fs/promises");
        await writeFile(`${dir}/input.${ext}`, bytes);
        await writeSession({
          sessionId,
          fileName: sanitizeFileName(file.name),
          fileSize: file.size,
          status: "uploaded",
          createdAt: new Date().toISOString(),
        });

        try {
          startWorkflow(sessionId, "profile");
        } catch (err) {
          console.error("[upload] could not start profiling:", err);
          return json({ error: "The profiler could not be started. Please try again." }, 500);
        }
        return json({ sessionId });
      },
    },
  },
});
