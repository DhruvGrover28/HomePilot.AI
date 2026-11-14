# Phase 1 report

## Built

- Replaced the finance-specific application surface with household configuration, injectable clock, SQLAlchemy/SQLite schema, seed data, and validated Pydantic inputs.
- Added pure Python consumption, anomaly, depletion, warranty, maintenance, carbon, cost and priority helpers.
- Added reading CRUD and all-or-nothing CSV import with row-level errors, appliance CRUD, inventory creation and quantity history, shopping-list and task APIs, and dashboard summary data.
- Added a simulated demo seed endpoint and a React dashboard with electricity and water charts and simulated badges.
- Preserved the original prototype in the `pre-homepilot-rework` tag.

## Verification

- Backend: `9 passed, 3 warnings` with `cd backend; python -m pytest tests -q`.
- Frontend: `npm run build --prefix frontend` completed successfully. Vite reports a non-blocking bundle-size warning.
- Live API verification passed on a clean SQLite database: health, empty dashboard, deterministic seed, seed idempotency, reading meter validation, all CRUD paths, successful CSV import, and all-or-nothing malformed CSV rejection.
- Live browser verification passed with a clean frontend/backend pair: empty dashboard, charts, demo seed button, simulated labels, and populated chart/record counts.
- Clock guard confirms direct `datetime.now` and `datetime.utcnow` calls are absent outside `clock.py`.

## Issues found and fixed during independent verification

- The repository-root pytest command failed because `app` is imported relative to `backend`; the README and checklist now document the working command from the backend module root.
- The old manual checklist targeted the retired finance upload endpoint; it now covers the household API and dashboard workflows.
- The claimed CRUD surface was incomplete; update/delete routes and regression coverage were added for readings, appliances, inventory, shopping-list items and tasks.
- The dashboard always displayed a simulated badge for appliances; it now respects each record's `is_simulated` value.
- Demo-seed failures are now surfaced in the frontend instead of silently reloading.

## Known limitations

- The old finance modules remain as unused compatibility files but are no longer routed by the application.
- Frontend dependency audit reports existing transitive vulnerabilities; no forced upgrade was applied during this phase.
- The frontend production bundle is larger than Vite's 500 kB advisory threshold.
- FastAPI emits a deprecation warning for the existing `on_event` startup hook.
- Deployment is postponed until all core phases are complete, per instruction.
- Live Gemini, Telegram, vision, agents, scheduling, n8n and deployment remain intentionally out of scope for Phase 1.

## Human action

- No Phase 1 credentials are required. Keep `LLM_MODE=mock`.
- Before Phase 4, provide the Gemini model name and API key, and the Telegram bot token.
- Before Phase 6, provide ready Vercel and Render accounts.

## Status

Phase 1 is independently verified and complete after the fixes above. No external integrations or credentials were required or tested.
