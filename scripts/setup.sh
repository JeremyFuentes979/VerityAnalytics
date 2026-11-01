#!/usr/bin/env bash
# One-time setup: Python virtualenv for the agents, npm packages for the site, and a .env to fill in.
set -euo pipefail
cd "$(dirname "$0")/.."

command -v python3 >/dev/null || { echo "python3 is required (3.9+)"; exit 1; }
command -v node >/dev/null || { echo "Node.js 20.12+ is required"; exit 1; }

if [ ! -d .venv ]; then python3 -m venv .venv; fi
.venv/bin/pip install --quiet --upgrade pip
.venv/bin/pip install --quiet -r requirements.txt
echo "Python agents ready (.venv)."

npm --prefix site install --no-audit --no-fund
echo "Site dependencies ready."

if [ ! -f site/.env ]; then
  cp site/.env.example site/.env
  echo "Created site/.env. Add your Stripe keys, or set VERITY_DEV_PAYMENT_BYPASS=1 for local testing."
fi

echo
echo "Next:  npm --prefix site run dev      (http://localhost:3000)"
echo "Test:  .venv/bin/python -m unittest discover -s tests -t .   and   npm --prefix site test"
