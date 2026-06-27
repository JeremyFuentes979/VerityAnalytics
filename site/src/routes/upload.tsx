import { createFileRoute, useNavigate } from "@tanstack/react-router";
import { createServerFn } from "@tanstack/react-start";
import { useState, useRef } from "react";

const uploadFile = createServerFn({ method: "POST" })
  .validator((data: unknown) => {
    if (typeof data !== "object" || data === null) throw new Error("Invalid request");
    const d = data as Record<string, unknown>;
    if (typeof d.fileName !== "string") throw new Error("fileName required");
    if (typeof d.fileContent !== "string") throw new Error("fileContent required");
    return { fileName: d.fileName, fileContent: d.fileContent };
  })
  .handler(async ({ data }) => {
    const { fileName, fileContent } = data;
    const sessionId = crypto.randomUUID();
    const sessionDir = `/home/team/shared/sessions/${sessionId}`;
    const fs = await import("node:fs/promises");
    await fs.mkdir(sessionDir, { recursive: true });

    const buffer = Buffer.from(fileContent, "base64");
    const ext = fileName.endsWith(".csv") ? "csv" : "xlsx";
    await fs.writeFile(`${sessionDir}/input.${ext}`, buffer);
    await fs.writeFile(
      `${sessionDir}/session.json`,
      JSON.stringify({ sessionId, fileName, status: "uploaded", createdAt: new Date().toISOString() })
    );

    return { sessionId };
  });

export const Route = createFileRoute("/upload")({
  component: Upload,
});

function Upload() {
  const navigate = useNavigate();
  const fileInputRef = useRef<HTMLInputElement>(null);
  const [dragOver, setDragOver] = useState(false);
  const [uploading, setUploading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const handleFile = async (f: File) => {
    setError(null);
    setUploading(true);

    const ext = f.name.split(".").pop()?.toLowerCase();
    if (!ext || !["csv", "xlsx", "xls"].includes(ext)) {
      setError("Accepted formats: .csv, .xlsx, .xls");
      setUploading(false);
      return;
    }

    const buffer = await f.arrayBuffer();
    const bytes = new Uint8Array(buffer);
    let binary = "";
    for (let i = 0; i < bytes.length; i++) binary += String.fromCharCode(bytes[i]);
    const base64 = btoa(binary);

    try {
      const result = await uploadFile({ data: { fileName: f.name, fileContent: base64 } });
      navigate({ to: `/preview/${result.sessionId}` });
    } catch {
      setError("Upload failed. Please try again.");
      setUploading(false);
    }
  };

  return (
    <div className="mx-auto max-w-2xl px-8 py-16">
      <div className="text-center">
        <span className="inline-block rounded-sm border border-navy-200 px-3 py-1 text-xs font-medium uppercase tracking-[0.15em] text-navy-500">
          New Engagement
        </span>
        <h1 className="mt-4 font-serif text-3xl font-bold text-navy sm:text-4xl">
          Submit Your Data
        </h1>
        <p className="mt-2 text-navy-500">
          Drop a CSV or Excel file below. Our Researcher will produce a free data profile — no charge, no commitment.
        </p>
      </div>

      <div
        className={`mt-10 rounded-sm border-2 border-dashed p-16 text-center transition-all ${
          dragOver
            ? "border-gold bg-gold-50"
            : "border-navy-200 hover:border-navy-400"
        }`}
        onDragOver={(e) => { e.preventDefault(); setDragOver(true); }}
        onDragLeave={() => setDragOver(false)}
        onDrop={(e) => { e.preventDefault(); setDragOver(false); const f = e.dataTransfer.files[0]; if (f) handleFile(f); }}
        onClick={() => fileInputRef.current?.click()}
      >
        <div className="flex flex-col items-center gap-4">
          <span className="text-4xl text-navy-300">📄</span>
          {uploading ? (
            <div className="flex items-center gap-3">
              <div className="h-4 w-4 animate-spin rounded-full border-2 border-navy border-t-transparent" />
              <span className="text-sm text-navy-500">Processing...</span>
            </div>
          ) : (
            <>
              <p className="font-medium text-navy">Drag a file here or click to browse</p>
              <p className="text-xs text-navy-400">Supports .csv, .xlsx, .xls — maximum 50 MB</p>
            </>
          )}
        </div>
        <input
          ref={fileInputRef}
          type="file"
          accept=".csv,.xlsx,.xls"
          className="hidden"
          onChange={(e) => { const f = e.target.files?.[0]; if (f) handleFile(f); }}
        />
      </div>

      {error && (
        <div className="mt-6 rounded-sm border border-red-200 bg-red-50 p-4 text-sm text-red-700">
          {error}
        </div>
      )}

      <div className="mt-10 rounded-sm border border-navy-100 bg-navy-50 p-6">
        <h3 className="text-sm font-bold uppercase tracking-wider text-navy">What to Expect</h3>
        <ol className="mt-4 space-y-2 text-sm text-navy-500">
          <li>1. We profile your data — schema, statistics, null analysis, and basic patterns</li>
          <li>2. You receive a free preview with everything we found</li>
          <li>3. Satisfied with the preview? Hire the firm for a one-time $50 fee to receive the full analysis, cleaned data, audit trail, and professional Excel workbook</li>
        </ol>
      </div>
    </div>
  );
}