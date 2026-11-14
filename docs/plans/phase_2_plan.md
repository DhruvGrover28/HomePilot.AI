# Phase 2 plan

## Scope

- Add a bounded household-analysis Supervisor.
- Route requests to energy, maintenance and inventory specialists.
- Persist completed agent runs with an inspectable execution trace.
- Keep the default path deterministic and offline in `LLM_MODE=mock`.
- Add a dashboard action that displays specialist recommendations and routing.

## Explicitly out of scope

- Live Gemini calls until credentials and a selected model are supplied.
- Telegram, vision, scheduling, n8n and deployment.
- Autonomous writes to household records.

## Verification

1. Run the complete backend pytest suite.
2. Run the frontend production build.
3. Exercise agent run creation, persistence, invalid-domain errors and missing-run errors over live HTTP.
4. Exercise empty and seeded analysis from the running browser application.
5. Record exact results in the Phase 2 report, update changelogs, commit and push.
