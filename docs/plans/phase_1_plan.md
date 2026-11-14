# Phase 1 plan

## Scope

- Replace the finance prototype with the HomePilot household foundation.
- Add one configuration module, an injectable clock, SQLite/SQLAlchemy models and initialization.
- Implement pure domain functions for consumption, depletion, status, scoring and estimates.
- Add validated reading, appliance, inventory, shopping-list and task APIs, including all-or-nothing CSV reading import.
- Add deterministic simulated seed data and a dashboard summary endpoint.
- Build a minimal React dashboard and data-entry view with charts and visible simulated labels.

## Decisions

- Database initialization uses SQLAlchemy `create_all` rather than Alembic for the four-day prototype; the schema is small and the initialization is repeatable.
- The prior transaction prototype is preserved in the `pre-homepilot-rework` tag and is not part of the new application surface.
- Phase 1 has no LLM, agent, Telegram, vision, n8n or deployment behavior. Seed data is explicitly simulated.
- Recharts is added because it is required by the specification and is the smallest charting dependency for the dashboard.

## Verification

1. Run the focused backend pytest suite, including domain edge cases and clock-source guard.
2. Start the API and exercise health, seed, summary and CSV validation endpoints.
3. Run the frontend production build.
4. Record results in `docs/reports/phase_1_report.md`, update `CHANGELOG.md`, commit, and push.
