import {
  HeadContent,
  Outlet,
  Scripts,
  createRootRoute,
  Link,
} from "@tanstack/react-router";
import type { ReactNode } from "react";

import appCss from "~/styles/app.css?url";

export const Route = createRootRoute({
  head: () => ({
    meta: [
      { charSet: "utf-8" },
      { name: "viewport", content: "width=device-width, initial-scale=1" },
      { title: "Quorum | Virtual Accounting & Analytics Firm" },
      { name: "description", content: "Transform messy financial data into trustworthy decisions. Hire a full virtual accounting firm on demand — no subscription required." },
    ],
    links: [
      { rel: "stylesheet", href: appCss },
      { rel: "preconnect", href: "https://fonts.googleapis.com" },
      { rel: "preconnect", href: "https://fonts.gstatic.com", crossOrigin: "anonymous" },
      { rel: "stylesheet", href: "https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&display=swap" },
    ],
  }),
  notFoundComponent: () => <div>Page not found</div>,
  component: RootComponent,
});

function RootComponent() {
  return (
    <RootDocument>
      <header className="border-b border-navy-100 bg-white">
        <div className="mx-auto flex max-w-6xl items-center justify-between px-8 py-4">
          <Link to="/" className="flex items-center gap-3">
            <div className="flex h-9 w-9 items-center justify-center rounded bg-navy text-sm font-bold tracking-wider text-white">
              Q
            </div>
            <div>
              <p className="text-lg font-bold tracking-tight text-navy">QUORUM</p>
              <p className="-mt-1 text-[10px] uppercase tracking-[0.2em] text-navy-400">
                Virtual Accounting &amp; Analytics
              </p>
            </div>
          </Link>
          <nav className="flex items-center gap-8 text-sm">
            <Link
              to="/"
              className="font-medium text-navy-500 transition-colors hover:text-navy"
              activeProps={{ className: "font-medium text-navy transition-colors" }}
            >
              Home
            </Link>
            <Link
              to="/upload"
              className="font-medium text-navy-500 transition-colors hover:text-navy"
              activeProps={{ className: "font-medium text-navy transition-colors" }}
            >
              Upload Data
            </Link>
            <Link
              to="/"
              className="rounded-md bg-navy px-5 py-2.5 text-sm font-medium text-white transition-colors hover:bg-navy-700"
            >
              Hire the Firm
            </Link>
          </nav>
        </div>
      </header>
      <main>
        <Outlet />
      </main>
      <footer className="border-t border-navy-100 bg-navy-50 py-12">
        <div className="mx-auto max-w-6xl px-8">
          <div className="flex flex-col items-center justify-between gap-4 text-center sm:flex-row sm:text-left">
            <div>
              <p className="text-sm font-bold text-navy">QUORUM</p>
              <p className="text-xs text-navy-400">Virtual Accounting & Analytics</p>
            </div>
            <p className="text-xs text-navy-400">
              &copy; {new Date().getFullYear()} Quorum. All rights reserved.
            </p>
          </div>
        </div>
      </footer>
    </RootDocument>
  );
}

function RootDocument({ children }: { children: ReactNode }) {
  return (
    <html lang="en">
      <head>
        <HeadContent />
      </head>
      <body>
        {children}
        <Scripts />
      </body>
    </html>
  );
}