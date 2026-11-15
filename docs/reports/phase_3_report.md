# Phase 3 report: Proactive household monitoring

## Status

Phase 3 implementation and local verification are complete. No commit or push
has been performed yet; that requires explicit user approval.

## Implemented

- Added a persistent `MonitoringIssue` model with stable fingerprints,
  evidence IDs, trigger provenance, issue status, investigation status and
  linked agent runs.
- Added one deterministic monitoring engine for scheduled, event-driven and
  manual checks.
- Added energy and water household-level fingerprints (`energy:anomaly` and
  `water:anomaly`) with separate latest evidence reading IDs.
- Added entity-specific appliance and inventory fingerprints.
- Added positive-only resolution for consumption, maintenance, warranty and
  inventory conditions.
- Added independent issue and investigation lifecycles.
- Added a process-local bounded executor with fixed workers, bounded active and
  pending capacity, transactional issue claiming, duplicate prevention,
  submission rejection handling, stale-claim recovery and independent worker
  database sessions.
- Added APScheduler startup/shutdown integration with one non-overlapping job.
- Added post-commit hooks for reading, CSV, appliance, inventory and task
  mutations.
- Added monitoring APIs:
  - `GET /api/monitoring/issues`
  - `GET /api/monitoring/issues/{issue_id}`
  - `POST /api/monitoring/check`
- Added dashboard monitoring visibility for issues, statuses, provenance,
  entity/evidence identity, findings and recommendations.
- Preserved the existing LangGraph Supervisor, specialists, provider
  orchestration, budgets and explicit provider exhaustion behavior.
- Added APScheduler `3.10.4` as the only new dependency.

## Verification completed

- Backend regression suite at Phase 3 completion: **45 passed, 13 warnings**.
- Focused monitoring and executor tests passed, including:
  - stable fingerprints and latest evidence;
  - positive-only resolution;
  - independent lifecycles;
  - bounded capacity and duplicate submission prevention;
  - scheduler non-overlap and shutdown registration;
  - monitoring API behavior and invalid-domain rejection.
- Frontend production build: passed.
- `git diff --check`: passed.
- Backend Python syntax compilation: passed.
- Empty isolated SQLite database: monitoring returned **0 issues**.
- Clean local FastAPI instance on port 8001:
  - `/health`: HTTP 200;
  - `POST /api/monitoring/check`: HTTP 200;
  - `GET /api/monitoring/issues`: HTTP 200.
- Existing local service on port 8000:
  - manual monitoring returned persisted issues;
  - a real inventory CRUD request created an entity-specific issue with
    `first_trigger_source=event`;
  - executor saturation persisted `investigation_status=interrupted` with a
    sanitized capacity message.

## Issues found and fixed

- Replaced dynamic SQLAlchemy imports in the executor with a normal `select`
  import.
- Fixed a staggered-provider completion race that could invoke a later
  provider after an earlier provider had already produced a valid result.
- Corrected the manual endpoint from `/run` to the approved `/check` path.
- Added a scheduler lifecycle regression test after full-suite validation.
- The empty-database temporary file was initially held open by SQLite on
  Windows; it was removed after interpreter exit.

## Known limitations and untested areas

- The local live workflow used the repository's existing runtime configuration;
  no new external provider call was required for this phase. Provider
  exhaustion and agent behavior remain covered by controlled tests, while
  external credentials/provider availability are not claimed as live Phase 3
  verification.
- The existing local database contained seeded/persistent records during the
  CRUD demonstration, so the empty-database result was verified separately in
  an isolated temporary database.
- FastAPI lifecycle and Pydantic/LangGraph deprecation warnings remain
  non-blocking.
- The frontend build retains the existing Vite bundle-size advisory.
- No consequential household action execution, notifications, distributed
  queue, deployment, Telegram, vision or n8n core workflow was added.

## Security and repository hygiene

- No secrets or `.env` files were printed, modified or staged.
- No deployment, commit or push was performed.
