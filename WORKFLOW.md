# Verity Analytics Team Workflow

## Code & Git Workflow

### Branch Strategy
- `main`: production-ready code. Always deployable.
- `feature/*`: feature branches for new work.
- `fix/*`: bug fix branches.

### Workflow
1. Create a feature branch from `main`.
2. Commit changes with clear messages.
3. Push and create a Pull Request.
4. The team lead reviews and merges (squash) into `main`.

### PR Conventions
- Title: `[Type] Short description` (e.g. `[Feat] Add Researcher ingestion module`)
- Description: what changed and why.
- Keep PRs focused on a single concern.

## Local Testing
- Setup once: `./scripts/setup.sh`
- Website: `npm --prefix site run dev` (dev) or `npm --prefix site run build && npm --prefix site run start` (prod)
- Whole pipeline on a session folder: `.venv/bin/python workflow/orchestrator.py <session-id> --stage profile|full`
  (the full stage requires `paidAt` in `session.json`; set `VERITY_ALLOW_UNPAID=1` to bypass for local debugging)
- Single agent: `.venv/bin/python agents/<agent>/<script>.py <session-dir>`
- Status: `node agents/concierge/status.js <session-id>`
- Tests: `.venv/bin/python -m unittest discover -s tests -t .` and `npm --prefix site test`
