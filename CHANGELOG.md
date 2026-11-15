# HomePilot AI Changelog

## Phase 5 - 2026-11-15
- Implemented end-to-end security and household isolation: scoped agent tools (`energy_readings`, `water_readings`, `maintenance_statuses`, `inventory_levels`), LangGraph `AgentState`, agent service, monitoring queries, and demo seeding by `household_id`, failing closed on missing context.
- Protected sensitive APIs with mandatory authentication (`get_current_household`) while keeping public health, login, and registration open.
- Added user profile management, theme preference (`light`, `dark`, `system`), password change, and household configuration (`timezone`, `preferred_units`, `onboarding_completed`).
- Built 4-step interactive onboarding wizard (`OnboardingWizard.jsx`) for new households.
- Redesigned frontend into a modular SaaS application shell with responsive navigation and dedicated specialist views:
  - `EnergyView.jsx`: Consumption metrics, daily rate chart, manual logging, CSV import.
  - `WaterView.jsx`: Volume tracking, daily rate chart, leak indicators, CSV import.
  - `MaintenanceView.jsx`: Appliance directory, warranty tracking, interactive tasks checklist.
  - `InventoryView.jsx`: Consumables stock levels, safety thresholds, stock adjusters, shopping list.
  - `MonitoringView.jsx`: Active engine issues, trigger provenance, occurrence counts, filter tabs.
  - `InvestigationsView.jsx`: Dynamic LangGraph Supervisor timeline visualization, candidate evaluations, tool traces, findings, and scored recommendations.
  - `AssistantView.jsx`: Conversational operational AI grounded in household telemetry with history persistence and linked investigation viewer.
  - `SettingsView.jsx`: Profile, household settings, password update, and scoped demo seeding.
- Added Render deployment blueprint (`render.yaml`) with PostgreSQL database resource and `psycopg[binary]` production engine support.

## Phase 4 - 2026-11-15
- Added deterministic Household Intelligence service (`intelligence.py`) and API endpoint (`GET /api/intelligence/summary`).
- Implemented cross-domain relationship discovery between consumption anomalies, appliance degradation, and inventory stockouts.
- Added evidence-based recommendation scoring, ranking, and suppression of ungrounded advice.
- Added comprehensive intelligence test coverage and regression test suites.

## Phase 3 - 2026-11-15
- Added shared deterministic scheduled, event-driven and manual household monitoring.
- Added persistent stable issue fingerprints, independent issue/investigation lifecycles and positive-only resolution.
- Added bounded background investigations, APScheduler lifecycle management, monitoring APIs and dashboard visibility.
- Added monitoring tests, API coverage and empty-database verification.

## Provider integration - 2026-11-14
- Added explicit Groq and OpenRouter provider selection for the existing LangGraph Supervisor while preserving Gemini and mock modes.
- Added staggered OpenRouter → Groq → Gemini application-level provider racing with sanitized attempt traces and controlled exhaustion.

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
