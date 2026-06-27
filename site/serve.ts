// Production server for the built site. The TanStack Start build emits a portable
// fetch handler (dist/server/server.js) plus static client assets (dist/client);
// this wraps them in a Bun server on port 3000 — static files first, SSR for the
// rest. Run `bun run build` before starting. Restart it with `bun run publish`.
//
// Starting a new instance supersedes the old one: it kills the previously
// recorded pid and takes over the port, so `publish` never collides with the
// already-running server.
import handler from "./dist/server/server.js";

const PORT = Number(process.env.PORT ?? 3000);
const HOST = process.env.HOST ?? "0.0.0.0";
const CLIENT_DIR = `${import.meta.dir}/dist/client`;
const PID_DIR = `${import.meta.dir}`;
const PID_FILE = `${PID_DIR}/team-site.pid`;

const prev = Number(await Bun.file(PID_FILE).text().catch(() => ""));
if (prev && prev !== process.pid) {
  try {
    process.kill(prev, "SIGKILL");
  } catch {
    // already gone
  }
  await Bun.sleep(500);
}
await Bun.write(PID_FILE, String(process.pid));

Bun.serve({
  port: PORT,
  hostname: HOST,
  async fetch(req) {
    const { pathname } = new URL(req.url);
    if (pathname !== "/") {
      const file = Bun.file(CLIENT_DIR + pathname);
      if (await file.exists()) return new Response(file);
    }
    return (
      handler as { fetch: (r: Request) => Response | Promise<Response> }
    ).fetch(req);
  },
});

console.log(`team-site serving on http://${HOST}:${String(PORT)}`);