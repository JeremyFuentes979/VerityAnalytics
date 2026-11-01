// Production server for the built site (Node 20.12+; no Bun required).
// The TanStack Start build emits a fetch handler (dist/server/server.js) plus static
// assets (dist/client). This serves static files first and falls back to SSR.
//
//   npm run build && npm run start
import { createReadStream, existsSync } from "node:fs";
import { stat } from "node:fs/promises";
import { createServer } from "node:http";
import { extname, join, normalize, resolve, sep } from "node:path";
import { Readable } from "node:stream";
import { fileURLToPath } from "node:url";

const ROOT = fileURLToPath(new URL(".", import.meta.url));
process.chdir(ROOT); // server code resolves ../sessions and ../.venv relative to site/

process.env.NODE_ENV ??= "production";
if (existsSync(join(ROOT, ".env"))) {
  try {
    process.loadEnvFile(join(ROOT, ".env")); // does not override variables already set
  } catch (err) {
    console.error("Could not read .env:", err);
  }
}

const PORT = Number(process.env.PORT ?? 3000);
const HOST = process.env.HOST ?? "0.0.0.0";
const CLIENT_DIR = resolve(ROOT, "dist", "client");
const MAX_BODY_BYTES = 60 * 1024 * 1024; // upload limit (50 MB) plus multipart overhead

if (!existsSync(join(ROOT, "dist", "server", "server.js"))) {
  console.error("No build found. Run `npm run build` first.");
  process.exit(1);
}
const { default: app } = await import("./dist/server/server.js");

const MIME = {
  ".html": "text/html; charset=utf-8",
  ".js": "text/javascript; charset=utf-8",
  ".mjs": "text/javascript; charset=utf-8",
  ".css": "text/css; charset=utf-8",
  ".json": "application/json; charset=utf-8",
  ".svg": "image/svg+xml",
  ".png": "image/png",
  ".jpg": "image/jpeg",
  ".ico": "image/x-icon",
  ".woff": "font/woff",
  ".woff2": "font/woff2",
  ".txt": "text/plain; charset=utf-8",
  ".map": "application/json",
};

const SECURITY_HEADERS = {
  "X-Content-Type-Options": "nosniff",
  "Referrer-Policy": "strict-origin-when-cross-origin",
  "X-Frame-Options": "SAMEORIGIN",
};

async function tryStatic(pathname, res, method) {
  let decoded;
  try {
    decoded = decodeURIComponent(pathname);
  } catch {
    return false;
  }
  const target = resolve(CLIENT_DIR, "." + normalize("/" + decoded));
  if (target !== CLIENT_DIR && !target.startsWith(CLIENT_DIR + sep)) return false; // path traversal
  let info;
  try {
    info = await stat(target);
  } catch {
    return false;
  }
  if (!info.isFile()) return false;

  const immutable = decoded.startsWith("/assets/");
  res.writeHead(200, {
    ...SECURITY_HEADERS,
    "Content-Type": MIME[extname(target).toLowerCase()] ?? "application/octet-stream",
    "Content-Length": info.size,
    "Cache-Control": immutable ? "public, max-age=31536000, immutable" : "public, max-age=300",
  });
  if (method === "HEAD") res.end();
  else createReadStream(target).pipe(res);
  return true;
}

/** Stream a request body, aborting once it exceeds the limit. */
function limitedBody(req) {
  let seen = 0;
  const source = Readable.toWeb(req);
  return source.pipeThrough(
    new TransformStream({
      transform(chunk, controller) {
        seen += chunk.byteLength;
        if (seen > MAX_BODY_BYTES) controller.error(new Error("Request body too large"));
        else controller.enqueue(chunk);
      },
    }),
  );
}

const server = createServer(async (req, res) => {
  try {
    const origin = `${req.headers["x-forwarded-proto"]?.split(",")[0] ?? "http"}://${req.headers.host ?? "localhost"}`;
    const url = new URL(req.url ?? "/", origin);

    if ((req.method === "GET" || req.method === "HEAD") && url.pathname !== "/") {
      if (await tryStatic(url.pathname, res, req.method)) return;
    }

    if (Number(req.headers["content-length"] ?? 0) > MAX_BODY_BYTES) {
      res.writeHead(413, { "Content-Type": "text/plain" }).end("Payload too large");
      return;
    }

    const hasBody = req.method !== "GET" && req.method !== "HEAD";
    const request = new Request(url, {
      method: req.method,
      headers: req.headers,
      body: hasBody ? limitedBody(req) : undefined,
      duplex: hasBody ? "half" : undefined,
    });

    const response = await app.fetch(request);
    const headers = {};
    response.headers.forEach((value, key) => {
      if (key !== "set-cookie") headers[key] = value;
    });
    const cookies = response.headers.getSetCookie?.() ?? [];
    res.writeHead(response.status, { ...SECURITY_HEADERS, ...headers, ...(cookies.length ? { "set-cookie": cookies } : {}) });

    if (!response.body || req.method === "HEAD") res.end();
    else Readable.fromWeb(response.body).on("error", () => res.destroy()).pipe(res);
  } catch (err) {
    console.error("[server] request failed:", err);
    if (!res.headersSent) res.writeHead(500, { "Content-Type": "text/plain" });
    res.end("Internal Server Error");
  }
});

server.listen(PORT, HOST, () => {
  console.log(`Verity Analytics serving on http://${HOST === "0.0.0.0" ? "localhost" : HOST}:${PORT}`);
});

for (const signal of ["SIGINT", "SIGTERM"]) {
  process.on(signal, () => server.close(() => process.exit(0)));
}
