# HomePilot AI Changelog

## Provider integration - 2026-11-14
- Added explicit Groq provider selection for the existing LangGraph Supervisor while preserving Gemini and mock modes.
- Added bounded Groq reasoning and JSON-schema Supervisor decision validation without automatic failover.

## Phase 2 - 2026-11-14
- Replaced fixed routing with LangGraph Supervisor orchestration and structured mock/live decisions.
- Added bounded Energy, Water, Maintenance and Inventory specialists, evidence-based findings, budgets and recommendation suppression.
- Added persisted agent traces and dashboard findings/recommendations.
- Live Gemini remains blocked by the configured model being unavailable to new users.

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
