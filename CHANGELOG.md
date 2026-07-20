# HomePilot AI Changelog

## Phase 1 - 2026-07-20
- Created monorepo structure for frontend, backend, n8n, and docs.
- Built FastAPI backend with CSV upload endpoint for transaction ingestion.
- Added Expense Agent using LangChain plus Gemini structured categorization.
- Implemented anomaly detection for unusually large and duplicate transactions.
- Stored analyzed transactions in SQLite.
- Built React plus Tailwind single-page dashboard for upload, table view, and anomalies.
- Added sample CSV and manual test checklist.
- Added setup and deployment instructions in README.
