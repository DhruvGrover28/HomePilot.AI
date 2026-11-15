# Phase 3 Plan: Proactive Household Monitoring

## Objective

Implement proactive household monitoring with one shared monitoring engine and
three trigger mechanisms:

- Scheduled checks through APScheduler.
- Event-driven checks from successful household data mutations.
- Manual checks through an API endpoint.

All three mechanisms must use the same deterministic detection, issue
deduplication, lifecycle management, background investigation submission, and
existing bounded LangGraph workflow.

Phase 3 must remain consistent with the completed Phase 1 household
foundation and Phase 2 Supervisor, specialist, persistence, safety, and
multi-provider implementations.

## Scope

### Included

- Deterministic monitoring for:
  - Electricity anomalies.
  - Water anomalies.
  - Appliance maintenance and warranty conditions.
  - Low inventory.
- APScheduler lifecycle integration.
- Lightweight post-commit event hooks.
- Manual monitoring checks.
- Persistent monitoring issues and investigation tracking.
- Entity-aware deduplication.
- Bounded process-local background investigations.
- Dashboard visibility for monitoring activity and investigation results.
- Tests for detection, triggers, deduplication, lifecycle, background capacity,
  provider exhaustion, persistence, APIs, and regression behavior.

### Excluded

- Telegram notifications.
- Computer vision.
- n8n workflows as a core requirement.
- Kafka, Redis, Celery, queues, or distributed event infrastructure.
- Cloud deployment.
- Complex notification systems.
- Automatic consequential household actions.
- New specialist-agent architectures.
- Heuristic provider fallback.
- Broad refactoring of functioning Phase 1 or Phase 2 code.

Recommendations remain informational. The LLM must not execute consequential
household actions.

## Existing architecture and reuse

The implementation will reuse:

- SQLAlchemy persistence and `create_all()` initialization.
- Existing reading, appliance, inventory, and task CRUD operations.
- Existing deterministic domain helpers.
- Existing Energy, Water, Maintenance, and Inventory tools.
- Existing LangGraph Supervisor and specialist workflow.
- Existing provider orchestration and explicit provider-exhaustion behavior.
- Existing `AgentRun` persistence and trace format.
- Existing React dashboard structure.

The monitoring layer will not create separate agents for scheduled and
event-driven checks.

## Proposed modules and changes

Expected implementation changes:

- `backend/requirements.txt`
  - Add APScheduler without unrelated dependency upgrades.
- `backend/app/config.py`
  - Add monitoring enabled/interval and bounded workload settings.
- `backend/app/db/models.py`
  - Add a `MonitoringIssue` model.
- `backend/app/schemas_monitoring.py`
  - Add monitoring issue, candidate, status, and API response schemas.
- `backend/app/services/monitoring.py`
  - Implement the shared monitoring engine, deterministic checks, fingerprints,
    issue lifecycle, provenance, background submission, and recovery.
- `backend/app/routers/monitoring.py`
  - Add monitoring issue reads and the manual check endpoint.
- `backend/app/routers/household.py`
  - Add post-commit event hooks for relevant mutations.
- `backend/app/main.py`
  - Start and stop the scheduler and monitoring executor safely.
- `frontend/src/App.jsx`
  - Add minimal monitoring activity and investigation visibility.
- `backend/tests/test_monitoring.py`
  - Add focused monitoring and lifecycle tests.
- Existing API/agent tests
  - Extend only where regression coverage is needed.
- `docs/reports/phase_3_report.md`, changelogs, and README
  - Update only during implementation closure.

No implementation files are changed by this plan document.

## Shared monitoring engine

The shared engine will expose one pathway conceptually equivalent to:

```text
evaluate_monitoring(trigger_source, affected_domains, context)
```

Supported trigger sources:

- `scheduled`
- `event`
- `manual`

The engine will:

1. Evaluate deterministic conditions.
2. Produce normalized issue candidates.
3. Compute a stable fingerprint.
4. Resolve only issues whose conditions are positively cleared.
5. Transactionally claim new actionable issues.
6. Prevent duplicate active investigation submissions.
7. Submit new investigations to the bounded process-local executor.
8. Update investigation status as the existing agent workflow progresses.
9. Return issue and investigation state to the caller.

The engine will never invoke an LLM merely to determine whether a
deterministic threshold or status condition has been crossed.

## Fingerprints and evidence identity

The current database represents one household through one database scope and
does not contain a separate household or meter entity. Therefore energy and
water fingerprints will be stable household/domain fingerprints:

```text
energy:anomaly
water:anomaly
```

Multiple anomalous readings can therefore represent one ongoing household
energy or water issue rather than creating a new issue for every reading.

The latest evidence reading ID will be stored separately in `details_json`,
for example:

```json
{
  "latest_evidence_reading_id": 42,
  "reading_type": "electricity"
}
```

If a future schema introduces household or meter entities, those IDs can be
added to the fingerprint without changing the engine contract.

Appliance and inventory fingerprints will remain entity-specific:

```text
appliance:{appliance_id}:maintenance_overdue
appliance:{appliance_id}:warranty_expiring
appliance:{appliance_id}:warranty_expired
inventory:{inventory_item_id}:low_stock
```

Task fingerprints, if task-state monitoring is included, will use:

```text
task:{task_id}:maintenance_state
```

## Separate issue and investigation lifecycles

Issue condition and investigation execution are independent concepts.
Completing, failing, exhausting, or interrupting an investigation must never
automatically resolve the underlying household issue.

### Issue status

Allowed issue statuses:

- `open`
- `resolved`

Transitions:

```text
new actionable candidate -> open
positive deterministic resolution condition -> resolved
resolved condition returns -> open
```

An issue remains `open` when:

- Its investigation is queued or running.
- Its provider is exhausted.
- Its investigation fails.
- Its investigation is interrupted.
- Data is missing or insufficient.

### Investigation status

Allowed investigation statuses:

- `not_started`
- `queued`
- `investigating`
- `completed`
- `provider_exhausted`
- `failed`
- `interrupted`

Transitions:

```text
new issue with no submission -> not_started
successful executor submission -> queued
worker begins existing agent workflow -> investigating
agent workflow completes -> completed
all configured providers fail -> provider_exhausted
unexpected worker/application failure -> failed
shutdown, stale claim recovery, or cancellation before completion -> interrupted
```

After a terminal investigation status, the issue remains `open` unless the
next deterministic monitoring check proves that the underlying condition has
been resolved. A later check may create a new investigation for the same open
issue only when the previous investigation is terminal and the configured
deduplication policy allows re-evaluation; it must never create concurrent
duplicate investigations.

## Monitoring persistence

Add a `MonitoringIssue` table with fields equivalent to:

- `id`
- `fingerprint` with uniqueness protection
- `issue_type`
- `domain`
- `entity_id` where applicable
- `title`
- `issue_status`
- `first_trigger_source`
- `last_trigger_source`
- `first_detected_at`
- `last_detected_at`
- `resolved_at`
- `occurrence_count`
- `latest_evidence_id` where applicable
- `details_json`
- `investigation_id`
- `investigation_status`
- `active_run_id`
- `latest_run_id`
- `claimed_at`
- `started_at`
- `completed_at`
- `last_error`

The existing `AgentRun` record remains the source for findings,
recommendations, decisions, and detailed execution traces.

## Trigger provenance

Every issue preserves:

- `first_trigger_source`
- `last_trigger_source`
- `first_detected_at`
- `last_detected_at`
- `occurrence_count`

For example, a scheduled detection followed by an event-driven detection
becomes:

```text
first_trigger_source = scheduled
last_trigger_source = event
```

The latest source must not overwrite the original source.
This is a compact current-state history model, not event sourcing.

## Deterministic resolution rules

Insufficient data, missing data, or evaluation errors never resolve an issue.

### Energy anomaly

Resolve only when a later comparable electricity evaluation has sufficient
history and is explicitly not anomalous. If no later reading exists or history
is insufficient, keep the issue open and retain the latest evidence ID.

### Water anomaly

Resolve only when a later comparable water evaluation has sufficient history
and is explicitly not anomalous. Missing or insufficient history leaves the
issue open.

### Appliance maintenance and warranty

Resolve a maintenance issue only when the appliance still exists and its
deterministic maintenance status is explicitly neither `due_soon` nor
`overdue`.

Resolve a warranty issue only when the warranty status is explicitly active
and outside the configured warning window.

Missing dates or incomplete appliance data leave the issue open.

### Inventory

Resolve a low-stock issue only when the inventory item still exists and its
current quantity is strictly greater than its reorder threshold.

Missing quantity data or an evaluation failure leaves the issue open.
Deletion handling must be explicit and must not treat a failed lookup as proof
that the household condition was resolved.

## Bounded background workload

The monitoring executor will be process-local and deliberately small.

Proposed initial limits:

- Fixed worker count: `2`.
- Maximum queued pending jobs: `4`.
- Maximum total active plus queued monitoring jobs: `6`.
- One active investigation per issue fingerprint.

The exact values will be configuration constants/settings and tested as
measurable limits rather than silently growing an unbounded queue.

### Submission behavior

Before submission, the engine transactionally claims the issue and sets:

```text
issue_status = open
investigation_status = queued
```

If the bounded executor accepts the job, the worker transitions it to
`investigating`.

If the executor is full or rejects submission:

- No exception is hidden.
- The issue remains `open`.
- The investigation becomes `interrupted`.
- `last_error` records a sanitized capacity/submission reason.
- The issue remains eligible for a later scheduled, event, or manual retry.
- No duplicate second submission is created immediately.

### Duplicate-submission prevention

An issue cannot be submitted when its investigation status is already:

- `queued`
- `investigating`

The claim and status update occur in one database transaction before executor
submission. A submission failure transitions the claim to `interrupted`,
allowing later recovery without leaving a permanently queued issue.

### Recovery

At startup and before scheduled checks:

- Stale `queued` or `investigating` records older than the configured claim
  timeout are marked `interrupted`.
- They remain `open`.
- A later monitoring evaluation may submit a new investigation.

During shutdown:

1. Stop APScheduler.
2. Reject new monitoring submissions.
3. Cancel queued futures where possible.
4. Mark queued and not-started work `interrupted`.
5. Shut down the executor with bounded, best-effort cancellation.
6. Allow already-running provider calls to finish within their existing finite
   provider timeouts.

The database is the source of truth; in-memory futures are only lifecycle
helpers and are not required for recovery.

## Scheduled monitoring

Add APScheduler to `backend/requirements.txt` without unrelated upgrades.

The application will own one scheduler instance:

- Start once during FastAPI startup.
- Register one non-overlapping periodic monitoring job.
- Use a configurable monitoring interval.
- Stop before the background executor shuts down.
- Call the shared engine with `trigger_source="scheduled"`.

The job evaluates all supported domains but submits investigations only for
new or retryable actionable issues.

## Event-driven monitoring

Add post-commit hooks to existing operations:

| Mutation | Evaluation |
|---|---|
| Electricity reading create/update | Energy |
| Water reading create/update | Water |
| CSV import | Each affected reading domain once after batch commit |
| Inventory create/update | Relevant inventory item |
| Appliance create/update | Relevant appliance |
| Relevant task create/update | Task or maintenance domain |

Hooks run only after successful commits and never hold a transaction while an
agent investigation runs.

Demo seeding and bulk setup must avoid launching duplicate monitoring work for
every inserted record.

## Manual monitoring

Add:

```text
POST /api/monitoring/check
GET  /api/monitoring/issues
GET  /api/monitoring/issues/{issue_id}
```

`POST /api/monitoring/check` must use the same engine, fingerprints,
deduplication transaction, bounded executor, and existing `run_agent(...)`
workflow as scheduled and event-driven triggers.

The endpoint should return issue IDs and current statuses without waiting for
the entire LLM investigation.

Responses will expose:

- Issue status.
- Investigation status.
- Trigger provenance.
- Latest evidence identity.
- Linked agent run.
- Findings and recommendations when available.
- Sanitized provider-exhaustion or submission-capacity information.

## Agent integration

For a newly claimed issue, the engine submits the existing bounded
`run_agent(...)` workflow with an issue-specific goal and affected domain.

The integration will preserve:

- Existing Supervisor and specialist budgets.
- Existing LangGraph topology.
- Existing provider selection and staggered execution.
- Explicit provider exhaustion.
- No automatic mock fallback.
- No heuristic findings.
- No duplicate specialist executions.

An investigation result updates only investigation fields and linked run
references. It does not resolve the issue.

## Frontend visibility

Extend the existing dashboard minimally to show:

- Detected issue title and domain.
- Entity identity where applicable.
- Issue status.
- Investigation status.
- First and latest trigger sources.
- Detection timestamps.
- Latest evidence ID where useful.
- Findings and recommendations from the linked agent run.
- Explicit provider exhaustion or interrupted status.

Recommendations remain informational. No approval or action-execution system
will be added without a separate approved scope.

## Execution priorities

Implementation should prioritize correctness and end-to-end reliability in
this order:

1. Monitoring contracts, fingerprints, independent lifecycles, and
   deterministic resolution.
2. Transactional issue claiming and bounded background submission.
3. Application shutdown and stale-job recovery.
4. Shared scheduled, event, and manual trigger integration.
5. API and persistence verification.
6. Minimal dashboard visibility.
7. Optional polish only after all acceptance tests pass.

The four-day allocation is a guide rather than a feature commitment. Work
should stop expanding once the core monitoring workflow is reliable.

## Testing strategy

### Deterministic engine

Test:

- Normal energy, water, maintenance, and inventory states.
- Anomaly and threshold detection.
- Empty database behavior.
- Insufficient history behavior.
- Stable domain fingerprints for energy and water.
- Entity-specific appliance and inventory fingerprints.
- Latest evidence ID updates.
- Positive-only resolution.

### Lifecycle

Test:

- Independent issue and investigation statuses.
- Every allowed investigation transition.
- Investigation completion does not resolve the issue.
- Provider exhaustion does not resolve the issue.
- Failure and interruption leave the issue open.
- Resolved issues reopen when the condition returns.

### Deduplication and provenance

Test:

- Repeated scheduled checks produce one issue.
- Scheduled followed by event-driven detection preserves both sources.
- Event-driven followed by manual detection preserves both sources.
- Concurrent submissions create one investigation.
- A terminal investigation can be retried without concurrent duplication.

### Background workload

Test:

- Maximum pending capacity is enforced.
- Executor rejection produces `interrupted`, sanitized error state.
- Rejected work remains retryable.
- Duplicate submissions are prevented.
- Shutdown stops new work and handles queued jobs.
- Stale persisted jobs are recovered on startup.
- A slow fake investigation does not block the CRUD response.

### Triggers and APIs

Test:

- Reading create/update hooks.
- Batch CSV evaluation once per affected domain.
- Inventory and appliance hooks.
- Relevant task hooks if task-state support is added.
- Manual endpoint uses the same engine path.
- Failed transactions do not trigger monitoring.

### Agent integration

Test:

- New issues launch the existing mock LangGraph workflow.
- Findings, recommendations, traces, and linked runs persist.
- Provider exhaustion is explicit.
- No mock fallback occurs in live mode.
- Existing budgets and no-duplicate-tool behavior remain intact.

### Application verification

- Run the backend regression suite.
- Run isolated monitoring API tests.
- Exercise empty and seeded databases.
- Exercise event-driven checks through actual CRUD API calls.
- Exercise manual checks through the API.
- Invoke scheduled jobs directly in tests without waiting for wall-clock time.
- Run the frontend production build.
- Run `git diff --check`.
- Perform local end-to-end verification before phase closure.

## Acceptance criteria

Phase 3 is complete only when:

1. Scheduled, event-driven, and manual triggers use one monitoring engine.
2. Energy and water use stable household/domain fingerprints.
3. Latest evidence reading IDs are stored separately.
4. Appliance and inventory fingerprints include entity IDs.
5. Issue and investigation statuses are independent.
6. Investigation completion or failure never automatically resolves an issue.
7. Resolution requires positive deterministic evidence.
8. Insufficient or missing data never resolves an issue.
9. Background workload has a measured bounded pending capacity.
10. Executor submission failures are persisted as interrupted/retryable state.
11. Duplicate active submissions are prevented.
12. Queued and investigating records are recoverable after restart.
13. CRUD requests return without waiting for the full agent investigation.
14. APScheduler starts, avoids overlapping jobs, and shuts down safely.
15. Findings, recommendations, traces, trigger provenance, and investigation
    status are visible through the API and dashboard.
16. Provider exhaustion is explicit and never becomes mock mode or fabricated
    evidence.
17. Empty and seeded database workflows behave correctly.
18. Backend tests pass.
19. Frontend production build passes.
20. No excluded infrastructure or integration is required.

## Risks and mitigations

| Risk | Mitigation |
|---|---|
| Background work outlives a request | Persist issue and investigation state before submission; return status immediately |
| Executor saturation | Fixed worker count and maximum pending capacity |
| Submission rejection leaves stuck issues | Persist `interrupted` investigation state and retry on later evaluation |
| Process crash loses futures | Reconcile stale persisted claims on startup |
| Active provider call cannot be force-cancelled | Preserve finite provider timeouts and mark process state accurately |
| Scheduled/event race | Transactional fingerprint claim and active-status duplicate guard |
| Broad energy/water fingerprints hide distinct meters | Current schema has no meter entity; use household/domain scope and retain latest evidence ID |
| Investigation result incorrectly clears issue | Separate issue and investigation lifecycles with positive-only resolution |
| SQLite concurrency limits | Keep process-local bounded execution; no distributed architecture |
| Provider instability | Preserve explicit provider exhaustion and no heuristic/mock fallback |
| Four-day scope expansion | Defer notifications, n8n, deployment, approvals, and unrelated refactoring |

## Explicit exclusions

- Telegram.
- Computer vision.
- n8n as a core workflow.
- Kafka, Redis, Celery, or message brokers.
- Cloud deployment.
- Complex notification systems.
- Consequential household action execution.
- Automatic heuristic fallback.
- New agent architecture.
- Broad Phase 1 or Phase 2 refactoring.

