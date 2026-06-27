# Quorum — Virtual Accounting & Analytics Firm

Transform messy financial data into trustworthy decisions and professional Excel workbooks.

## Architecture

Quorum uses a multi-agent "division of labor":

- **Researcher** — Data ingestion, profiling, and external reference data
- **Analyst** — Exploratory data analysis, anomaly detection, pattern recognition
- **Auditor** — Data validation, cleaning, deduplication, and audit trail
- **Manager** — Conflict resolution, decision memo, and Excel workbook generation
- **Concierge** — User-facing communication layer and status tracking

## Quick Start

```bash
# Site
cd site && bun install && bun run dev

# Agents
python3 /home/team/shared/workflow/orchestrator.py <session-id>
```
