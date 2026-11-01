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
      { title: "Verity Analytics | Virtual Accounting & Analytics Firm" },
      { name: "description", content: "Transform messy financial data into trustworthy decisions. Hire a full virtual accounting firm on demand — no subscription required." },
    ],
    links: [
      { rel: "icon", href: "data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 32 32'%3E%3Crect width='32' height='32' rx='5' fill='%230a1e47'/%3E%3Ctext x='16' y='23' font-family='Georgia,serif' font-size='20' font-weight='700' text-anchor='middle' fill='%23ffffff'%3EV%3C/text%3E%3C/svg%3E" },
      { rel: "stylesheet", href: appCss },
      { rel: "preconnect", href: "https://fonts.googleapis.com" },
      { rel: "preconnect", href: "https://fonts.gstatic.com", crossOrigin: "anonymous" },
      { rel: "stylesheet", href: "https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&display=swap" },
    ],
  }),
  notFoundComponent: () => (
    <div className="mx-auto max-w-2xl px-8 py-24 text-center">
      <p className="font-serif text-2xl font-bold text-navy">Page not found</p>
      <Link to="/" className="mt-6 inline-block text-sm text-navy-500 underline hover:text-navy">Back to home</Link>
    </div>
  ),
  component: RootComponent,
});

function RootComponent() {
  return (
    <RootDocument>
      <header className="border-b border-navy-100 bg-white">
        <div className="mx-auto flex max-w-6xl items-center justify-between px-8 py-4">
          <Link to="/" className="flex items-center gap-3">
            <div className="flex h-9 w-9 items-center justify-center rounded bg-navy text-sm font-bold tracking-wider text-white">
              V
            </div>
            <div>
              <p className="text-lg font-bold tracking-tight text-navy">VERITY ANALYTICS</p>
              <p className="-mt-1 text-[10px] uppercase tracking-[0.2em] text-navy-500">
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
              to="/upload"
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
              <p className="text-sm font-bold text-navy">VERITY ANALYTICS</p>
              <p className="text-xs text-navy-500">Virtual Accounting & Analytics</p>
            </div>
            <p className="text-xs text-navy-500">
              &copy; {new Date().getFullYear()} Verity Analytics. All rights reserved.
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