# Quorum Team Workflow

## Code & Git Workflow

### Branch Strategy
- `main` — production-ready code. Always deployable.
- `feature/*` — feature branches for new work.
- `fix/*` — bug fix branches.

### Workflow
1. Create a feature branch from `main`.
2. Commit changes with clear messages.
3. Push and create a Pull Request.
4. The team lead reviews and merges (squash) into `main`.

### PR Conventions
- Title: `[Type] Short description` (e.g. `[Feat] Add Researcher ingestion module`)
- Description: What changed and why.
- Keep PRs focused on a single concern.

## Local Testing
- Website: `cd site && bun run dev` (dev mode) or `bun run publish` (prod rebuild)
- Modules: `python3 /home/team/shared/<agent>/main.py <session-dir>`
- Status: `node /home/team/shared/concierge/status.js <session-id>`