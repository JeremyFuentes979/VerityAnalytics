# Verity Analytics: Virtual Accounting & Analytics Firm

Transform messy financial data into trustworthy decisions and professional Excel workbooks.
Upload a file, get a free data profile, then hire the "firm" for a flat $50 to receive a cleaned
dataset, a full audit trail, a decision memo and an Excel workbook.

## Architecture

A multi-agent "division of labor". Each agent is a small script that reads and writes files in
`sessions/<id>/`:

| Agent | Script | Job |
| --- | --- | --- |
| Researcher | `agents/researcher/` | Ingest CSV / Excel / PDF, normalise to `raw/data.csv`, write `profile.json` (the free preview) |
| Analyst | `agents/analyst/` | Pattern analysis, outlier detection, data-quality hypotheses → `analysis.json` |
| Auditor | `agents/auditor/` | Conservative cleaning with a full audit trail → `cleaned_data.csv`, `audit_trail.json` |
| Manager | `agents/manager/` | Resolve Analyst/Auditor findings, decision memo, Excel workbook → `final_workbook.xlsx` |
| Concierge | `agents/concierge/` | Status and message templates for the user-facing layer |

`workflow/orchestrator.py` chains them. `site/` is the web app (TanStack Start + React + Tailwind).

**Auditor policy:** it auto-fixes only whitespace, exact duplicate rows and case/spacing variants of
category labels, and logs every change. Negative amounts and missing values are *flagged, never changed*,
because they may be legitimate credits, refunds or blanks.

## Flow and payment safety

```
upload ──► profile (free, automatic) ──► preview ──► Stripe Checkout ──► paid ──► full workflow ──► download
```

* `POST /api/upload` validates type, size and content, creates a session and starts the free profile.
* Checkout creates a **server-side Stripe Checkout Session** for exactly $50.
* A session becomes `paid` only after Stripe confirms it: through the signed webhook
  (`POST /api/stripe-webhook`, signature verified) and/or when the buyer returns to
  `/results/<id>` (the server re-fetches the Checkout Session from Stripe). Both paths check the
  session id, the amount and `payment_status === "paid"`, and are idempotent.
* The orchestrator itself **refuses to run the paid stage** for a session without `paidAt`, and
  `/api/download/<id>` returns 402 until the session is paid and complete.
* Session ids must be UUIDs and the orchestrator is started with an argument array (no shell).

## Setup

Requires Python 3.9+ and Node 20.12+ (no Bun needed).

```bash
./scripts/setup.sh                 # venv + packages + creates site/.env
```

Edit `site/.env` (see `site/.env.example`):

* `STRIPE_SECRET_KEY`: from the Stripe dashboard (use `sk_test_...` first).
* `STRIPE_WEBHOOK_SECRET`: signing secret of a webhook endpoint at `{SITE_URL}/api/stripe-webhook`
  for the `checkout.session.completed` event. Locally: `stripe listen --forward-to localhost:3000/api/stripe-webhook`.
* `SITE_URL`: the public URL (used for Stripe redirects).
* `VERITY_DEV_PAYMENT_BYPASS=1`: skip Stripe while developing. **Ignored when `NODE_ENV=production`.**

## Run

```bash
npm --prefix site run dev          # development, http://localhost:3000
npm --prefix site run build && npm --prefix site run start   # production (node serve.mjs)
```

## Test

```bash
.venv/bin/python -m unittest discover -s tests -t .   # agents + orchestrator, 20 tests
npm --prefix site test                                  # session id validation
npm --prefix site run typecheck
```

## Operations

* **Customer data lives in `sessions/`** (gitignored). Purge old sessions regularly:
  `python3 scripts/purge_sessions.py --days 30 --delete` (omit `--delete` for a dry run).
* Each run's compute time per agent is recorded in `session.json` (`agentSeconds`, `totalSeconds`),
  which feeds the gross-margin-per-run KPI.
* Per-session logs: `sessions/<id>/workflow.log`.
* Environment overrides: `VERITY_PYTHON`, `VERITY_SESSIONS_DIR`, `VERITY_REPO_ROOT`, `PORT`, `HOST`.

## Limits

50 MB per upload; Excel output is capped at 1,000,000 data rows; scanned PDFs need OCR (not supported);
only the first sheet of an Excel file is read.
