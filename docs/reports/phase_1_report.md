# Phase 1 report

## Built

- Replaced the finance-specific application surface with household configuration, injectable clock, SQLAlchemy/SQLite schema, seed data, and validated Pydantic inputs.
- Added pure Python consumption, anomaly, depletion, warranty, maintenance, carbon, cost and priority helpers.
- Added reading CRUD and all-or-nothing CSV import with row-level errors, appliance CRUD, inventory creation and quantity history, shopping-list and task APIs, and dashboard summary data.
- Added a simulated demo seed endpoint and a React dashboard with electricity and water charts and simulated badges.
- Preserved the original prototype in the `pre-homepilot-rework` tag.

## Verification

- Backend: `8 passed` with `pytest backend/tests -q`.
- Frontend: `npm run build` completed successfully from `frontend`.
- CSV validation test confirms malformed rows return HTTP 422 with row numbers.
- Clock guard confirms direct `datetime.now` and `datetime.utcnow` calls are absent outside `clock.py`.

## Changed from specification

- Phase 1 uses SQLAlchemy `create_all` instead of Alembic; this is documented in the phase plan and is sufficient for the prototype schema.
- The frontend is a focused dashboard rather than the complete later-phase multi-page UI.
- Live Gemini, Telegram, vision, agents, scheduling, n8n and deployment remain intentionally out of scope for Phase 1.

## Known limitations

- The old finance modules remain as unused compatibility files but are no longer routed by the application.
- Frontend dependency audit reports existing transitive vulnerabilities; no forced upgrade was applied during this phase.
- Deployment is blocked until the Vercel and Render accounts are ready.

## Human action

- No Phase 1 credentials are required. Keep `LLM_MODE=mock`.
- Before Phase 4, provide the Gemini model name and API key, and the Telegram bot token.
- Before Phase 6, provide ready Vercel and Render accounts.
