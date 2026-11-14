# HomePilot AI Changelog

## Phase 1 - 2026-11-14
- Reworked the finance prototype into the HomePilot household foundation.
- Added SQLAlchemy SQLite household models, configuration, injectable clock and simulated seed data.
- Added tested domain helpers for consumption, anomalies, inventory depletion, maintenance, warranty, carbon, cost and priority.
- Added household CRUD APIs, transactional CSV reading import, dashboard summary and demo endpoints.
- Added a React dashboard with electricity and water charts and simulated-data badges.
- Independent verification fixed the stale test checklist, completed CRUD routes, respected per-record simulated labels, and added regression coverage.

## Phase 1 - 2026-07-20
- Created monorepo structure for frontend, backend, n8n, and docs.
- Built FastAPI backend with CSV upload endpoint for transaction ingestion.
- Added Expense Agent using LangChain plus Gemini structured categorization.
- Implemented anomaly detection for unusually large and duplicate transactions.
- Stored analyzed transactions in SQLite.
- Built React plus Tailwind single-page dashboard for upload, table view, and anomalies.
- Added sample CSV and manual test checklist.
- Added setup and deployment instructions in README.
