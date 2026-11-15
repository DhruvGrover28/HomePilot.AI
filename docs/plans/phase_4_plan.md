# Phase 4 Plan: Evidence-Driven Household Intelligence

## Status

This is a planning document only. Phase 4 implementation requires separate
approval. Production deployment, security hardening, operational work and
final demo preparation remain Phase 5 responsibilities.

## 1. Current-state assessment

### Existing capabilities

HomePilot AI already has the core architecture needed for Phase 4:

- A LangGraph Supervisor with dynamic specialist decisions.
- Four existing specialists:
  - Energy.
  - Water.
  - Maintenance.
  - Inventory.
- Structured `Finding`, `Recommendation` and `SupervisorDecision` models.
- Evidence-aware follow-up through `suggested_next_investigation`.
- Supervisor and specialist budgets.
- Gemini, Groq and OpenRouter provider handling with explicit exhaustion.
- Persisted agent runs containing findings, decisions, recommendations and
  traces.
- A shared deterministic monitoring engine for scheduled, event-driven and
  manual checks.
- Persistent monitoring issues with stable fingerprints, investigation
  lifecycles and linked agent runs.
- A React dashboard that displays monitoring issues and individual analysis
  results.

The relevant existing implementation is in:

- `backend/app/services/agent_graph.py`
- `backend/app/services/agent_service.py`
- `backend/app/services/agent_tools.py`
- `backend/app/services/monitoring.py`
- `backend/app/services/monitoring_executor.py`
- `backend/app/db/models.py`
- `backend/app/schemas_agents.py`
- `frontend/src/App.jsx`

### Gaps Phase 4 should address

1. Monitoring investigations currently submit only the originating issue
   domain. Related open issues are not provided as structured context.
2. The Supervisor can follow a finding's suggested next investigation, but
   Phase 4 does not yet demonstrate a multi-domain investigation selected from
   persisted household evidence.
3. Recommendation scoring currently uses fixed values for several factors and
   does not provide a defensible household-wide ranking.
4. Monitoring issues and recommendations are not presented in one consolidated
   household-level view.
5. Consumption and inventory statistics contain reusable deterministic
   primitives, but forecasting is not integrated or validated.

Phase 4 must improve these gaps without claiming that the existing dynamic
Supervisor is absent. Cross-agent routing already exists; the change is to
make its context, evidence transitions and end-to-end behavior materially
stronger.

## 2. Precise objectives

Phase 4 has four objectives, in priority order:

1. Make the existing Supervisor perform evidence-driven cross-domain
   investigations.
2. Provide defensible, deterministic and explainable prioritisation for open
   issues and recommendations.
3. Produce a consolidated household intelligence view from existing persisted
   issues, findings and recommendations.
4. Verify the complete local workflow across monitoring, Supervisor routing,
   persistence, API and dashboard.

Forecasting is not an essential objective. It may be added only as a small
gated enhancement after the four objectives above are complete and reliable.

## 3. Essential and optional scope

### Essential

- Structured investigation context for the existing Supervisor.
- Related-issue discovery for monitoring investigations.
- Evidence-driven dynamic specialist selection.
- Evidence-linked cross-domain findings and decisions.
- Explainable prioritisation using a deterministic ranking policy.
- A household intelligence summary API.
- Minimal dashboard visibility for ranking, relationships, findings and
  recommendations.
- Empty, seeded, single-domain and multi-domain end-to-end verification.
- Preservation of existing provider, budget, lifecycle and retry behavior.

### Optional, gated

- One evidence-labelled consumption trend warning or inventory depletion
  estimate, reusing existing deterministic functions.

The optional feature must be abandoned for this phase if it requires new
infrastructure, a new agent, a new persistence lifecycle or compromises the
cross-agent demonstration.

## 4. Architecture and data flow

```text
MonitoringIssue records and household data
                |
                v
Deterministic investigation context
                |
                +--> related issue selection
                +--> priority ordering
                +--> evidence summaries
                |
                v
Existing bounded run_agent workflow
                |
                v
Existing LangGraph Supervisor
                |
       +--------+--------+--------+--------+
       v                 v        v        v
    Energy            Water  Maintenance Inventory
       |                 |        |        |
       +-------- structured findings and evidence
                |
                v
       Supervisor evaluates findings and decides
       whether another relevant specialist is needed
                |
                v
       Existing AgentRun persistence
                |
                v
       Deterministic household intelligence aggregation
                |
                +--> API
                +--> dashboard
```

There will be no new Decision Engine. Deterministic code will prepare
evidence, calculate ranking and aggregate persisted results. The Supervisor
will remain responsible for deciding which specialist to investigate next.

No request-scoped SQLAlchemy sessions or ORM instances may enter the
background workflow. Investigation context must contain IDs and serializable
snapshots only.

## 5. Dynamic cross-agent reasoning design

### Investigation context

When a monitoring investigation is claimed, the system will construct a
bounded serializable context containing:

- Primary monitoring issue ID, fingerprint, type, domain and title.
- Current issue status and investigation status.
- Latest deterministic evidence summary.
- Up to two related open issues from other domains.
- Related issue IDs, fingerprints, titles and latest evidence summaries.
- Current priority factors for the included issues.
- Requested investigation domains, limited by the existing agent-run domain
  contract.

The context must be a snapshot. The worker must not retain an ORM object or
open transaction while the agent workflow runs.

The context may be represented as an optional field on the existing agent
request/state models. Existing callers that do not provide context must retain
their current behavior.

### Selection of related issues

Related issues must be selected by deterministic relevance, not by a fixed
domain order. Relevance may use:

- The primary issue's domain and issue type.
- Shared appliance/entity identity where available.
- Existing `suggested_next_investigation`.
- Evidence references and compatible issue categories.
- Current open status.
- Priority ordering as a tie-breaker.

The implementation must cap context size. It must not pass every historical
issue into every LLM decision.

### Deterministic relationship classifications

The intelligence layer, not the LLM, classifies relationships between issues:

- **Confirmed relationship:** the issues share the same appliance or inventory
  entity, or a deterministic evidence rule directly connects them. For
  example, an energy anomaly and an overdue maintenance issue for the same
  appliance are confirmed related when the appliance identity is present in
  both records.
- **Plausible relationship:** the domains and evidence are compatible, but the
  database does not prove a direct entity relationship. For example, a
  household energy anomaly and an appliance maintenance issue without a shared
  appliance ID may be plausible related context.
- **Unrelated:** the issues have no supported entity, domain or evidence
  connection, or the available data is insufficient to establish even a
  plausible relationship.

Only confirmed and bounded plausible relationships may enter investigation
context. Unrelated issues must be excluded. The classification, rule matched,
source issue IDs and confidence state must be recorded in the context and
report. The Supervisor may decide whether a related specialist is needed, but
it may not invent or upgrade a relationship.

### Supervisor behavior

The existing LangGraph topology remains:

```text
Supervisor -> selected specialist -> Supervisor -> ... -> finalize
```

The Supervisor must receive:

- The original goal.
- Primary and related issue context.
- Findings already produced.
- Remaining candidate domains.
- Budget state.

Each decision must record:

- Selected specialist, if any.
- Rationale.
- Number and identity of findings considered.
- Context issue IDs considered.
- Provider/model metadata where available.

The Supervisor may:

- Select the primary specialist.
- Select a related specialist when evidence justifies it.
- Stop when evidence is sufficient.
- Stop when no relevant specialist remains.
- Stop when the existing budget is exhausted.

The implementation must not:

- Execute Energy, Water, Maintenance and Inventory in a fixed sequence.
- Select a specialist merely because it has not yet run.
- Add a fifth specialist.
- Bypass the Supervisor for cross-domain routing.
- Treat provider exhaustion as a successful investigation.

### Required demonstration

The principal demo scenario must prove:

```text
Energy anomaly and related appliance maintenance evidence exist.
The Supervisor selects Energy.
Energy evidence indicates that Maintenance is relevant.
The next Supervisor decision selects Maintenance.
Water and Inventory are not selected.
The final result explains the cross-domain relationship.
```

A contrasting test must show that an energy anomaly without supporting
maintenance evidence does not force a Maintenance investigation.

The final investigation output must explicitly explain all of the following:

1. What the original monitoring issue was.
2. What evidence the Energy specialist observed.
3. Why the Supervisor selected Maintenance next.
4. What Maintenance confirmed or ruled out.
5. How the combined evidence changed or supported the final recommendation.

The explanation must be traceable to persisted findings and deterministic
relationship classifications. A generic statement that multiple specialists
ran is not sufficient.

## 6. Defensible prioritisation

### Meaning of the ranking

The ranking represents **investigation priority**, not probability of failure,
financial risk or recommendation quality. It answers:

> Which open issue should the household investigate first, based on currently
> available evidence?

It must not claim precision that the data does not support.

### Avoiding arbitrary weights

The first implementation should use a lexicographic priority key rather than
an arbitrary weighted sum:

```text
priority_key = (
    severity_level,
    urgency_level,
    impact_level,
    confidence_level,
    evidence_completeness_level,
    corroboration_level,
    actionability_level,
    stable_tie_breaker
)
```

Each component is a small documented ordinal scale, such as `0`, `1`, `2`
or `3`. Keys are compared from left to right. A lower factor cannot
artificially outweigh a higher-priority factor.

The API should expose both the ordered factors and the resulting rank. A
display score may be derived from the rank for presentation, but it must not
be presented as a probability or scientific risk value.

### Severity and confidence interaction

Severity describes the seriousness of the condition if it is real. Confidence
describes how strongly the available evidence supports that condition. They
must remain separate.

For monitoring issues, a weakly evidenced high-severity candidate must not
automatically outrank a strongly confirmed lower-severity issue. The
monitoring ranking therefore uses this policy:

1. A confirmed deterministic condition is eligible for the main ranking.
2. Among eligible conditions, compare severity first, then urgency and impact.
3. If two conditions have different evidence completeness or confidence, the
   condition with complete evidence and higher confidence wins when the
   severity difference is not itself decisive.
4. An insufficient-data or unresolved-unknown condition cannot outrank a
   complete confirmed condition solely because its hypothetical severity would
   be high.
5. Unknown or incomplete data remains visible as a warning, but is placed in
   an evidence-limited group after confirmed actionable issues unless it has
   an explicit deterministic urgency signal.

This is a deterministic eligibility-and-lexicographic policy, not a weighted
severity multiplied by confidence formula. It prevents weak evidence from
masquerading as a confirmed high-priority condition while preserving serious
confirmed issues at the top.

### Monitoring-issue ranking policy

Monitoring issue priority is an investigation ordering. Its comparison key is:

```text
monitoring_key = (
    evidence_state,          # confirmed before evidence_limited
    severity_level,
    urgency_level,
    impact_level,
    confidence_level,
    evidence_completeness,
    corroboration_level,
    actionability_level,
    fingerprint
)
```

`evidence_state` is determined by the deterministic monitoring rule, not by an
LLM. `fingerprint` is the final stable tie-breaker. Resolved issues are
excluded. This policy deliberately prevents a speculative issue from
outranking a confirmed issue through severity alone.

### Recommendation ranking policy

Recommendation priority is separate from monitoring issue priority. It answers:

> Which evidence-linked, non-consequential recommendation is most useful to
> present first?

Recommendations are ranked by:

```text
recommendation_key = (
    recommendation_status,
    benefit_level,
    urgency_level,
    evidence_support_level,
    feasibility_level,
    source_issue_priority,
    recommendation_id
)
```

The factors have these meanings:

- `recommendation_status`: active and not suppressed before duplicate,
  dismissed or superseded recommendations.
- `benefit_level`: deterministic or finding-supported expected household
  benefit, not an invented financial value.
- `urgency_level`: deadline, threshold or worsening condition from the source
  evidence.
- `evidence_support_level`: strength and completeness of the linked finding
  and source issue.
- `feasibility_level`: whether the household can review or perform the
  informational action using existing data, without HomePilot executing it.
- `source_issue_priority`: the already computed monitoring priority as a
  lower-order factor.

Missing benefit, urgency, evidence or feasibility is conservative and never
receives the highest level. Duplicate or suppressed recommendations are not
ranked as active recommendations. Recommendation IDs provide stable final
tie-breaking. No arbitrary weighted score is required.

### Factor definitions

#### Severity

Severity comes from existing deterministic issue types and structured
findings:

- Informational or insufficient evidence: lowest level.
- Warning or approaching threshold: middle level.
- Confirmed anomaly, overdue maintenance or stockout: highest applicable
  level.

The mapping must be centralized and tested.

#### Urgency

Urgency comes from measurable time or threshold information:

- Overdue or already below threshold: highest applicable urgency.
- Due soon, expiring soon or rapidly worsening: intermediate urgency.
- No immediate deadline: lower urgency.

Missing dates do not receive high urgency merely because they are missing.

#### Impact

Impact must use available household evidence:

- Magnitude of a confirmed consumption deviation.
- Number or quantity of affected items.
- Whether a critical threshold has been crossed.
- A configured tariff only when present and clearly labelled.

When impact cannot be measured, the factor remains unknown or conservative.

#### Confidence

Confidence comes from structured finding confidence and deterministic
evidence quality. It is not inferred from the number of LLM words or from
provider identity.

#### Evidence completeness

This reflects whether the issue has the minimum evidence required for its
condition:

- Complete comparable history or complete entity fields: highest.
- Partial but usable evidence: intermediate.
- Missing or insufficient evidence: lowest.

Incomplete evidence must reduce confidence and ranking support; it must never
be converted into a fabricated severe condition.

#### Cross-domain corroboration

Corroboration is a tie-breaker or lower-order factor. It may increase
investigation priority when independent persisted evidence supports the same
household concern, but it must not independently create an issue or change
its severity.

#### Actionability

Actionability is based on whether the existing system can provide a concrete,
non-consequential recommendation, such as reviewing a reading or servicing
an appliance. It does not mean that HomePilot will execute the action.

Recommendation benefit, urgency, evidence support and feasibility are
calculated separately under the recommendation policy above. They must not be
collapsed into the monitoring issue's severity or confidence.

### Missing evidence and ties

- Missing evidence lowers evidence completeness and confidence.
- Missing data never increases priority.
- Confirmed conditions are not displaced by evidence-limited conditions solely
  because of a higher hypothetical severity.
- Monitoring ties are ordered by stable fingerprint, then detection time.
- Recommendation ties are ordered by stable recommendation ID.
- Resolved issues are excluded from the open-issue ranking by default.
- The ranking is recomputed when deterministic evidence or linked findings
  change.

## 7. Household intelligence reporting

### Report contents

The report is a deterministic aggregation of existing persisted data and
should contain:

- Ranked open issues.
- Issue and investigation statuses.
- Primary and related issue relationships.
- First and latest trigger provenance.
- Latest deterministic evidence identifiers.
- Latest linked findings.
- Evidence-linked recommendations.
- Provider exhaustion, interruption and insufficient-data warnings.
- Important trend or state changes already supported by deterministic tools.

The report must identify source issue IDs and agent run IDs for every finding
and recommendation. It must not merge unrelated findings solely because they
have similar wording.

Relationship classifications must be visible in the report. Confirmed,
plausible and unrelated relationships must remain distinguishable, and only
confirmed or bounded plausible relationships may be presented as related
household context.

### No separate reporting agent

The first report implementation should not call an LLM. It should aggregate
existing records and traces. This is more reliable, cheaper and easier to
test.

If a future version adds natural-language explanation, it must reuse the
existing Supervisor workflow and remain optional. It must not become a second
report-generation agent architecture.

### Empty and seeded reports

- Empty database: valid report with empty ranked issues, no false warnings and
  an explicit no-evidence state.
- Seeded database: report shows simulated-data labels and does not present
  simulated values as real household measurements.
- Mixed data: report preserves evidence provenance and confidence.

## 8. Optional forecasting decision

Forecasting is excluded from the essential Phase 4 acceptance criteria.

After all essential work passes, the team may evaluate one small enhancement:

### Candidate: evidence-labelled inventory depletion estimate

Reuse the existing inventory log and `depletion_estimate` functionality to
show:

- Average daily use.
- Estimated days remaining.
- Estimated run-out date.
- Evidence count and confidence.

The candidate must require enough positive consumption history. No numeric
estimate is returned when usage is zero, history is absent or the result is
unstable. The result is labelled an estimate and never creates, resolves or
changes a monitoring issue.

If integrating inventory history safely requires schema changes, broad data
backfills or a new persistence lifecycle, forecasting is deferred rather
than forced into Phase 4.

Energy or water machine-learning forecasts are explicitly excluded. Existing
baseline and trend helpers may support warnings in a later phase, but they
are not required here.

## 9. Database, API and frontend impact

### Database restraint

The first implementation must attempt to use existing data:

- `MonitoringIssue.details_json`.
- Monitoring lifecycle fields.
- `AgentRun.trace_json`.
- Existing findings and recommendation structures.
- Existing inventory logs and readings.

No new tables or columns are planned initially.

Priority and report data should be computed from these records unless tests
demonstrate a query, size or durability requirement that cannot be met.

If schema changes become necessary, the implementation must:

1. Explain the specific demonstrated need.
2. Add only the smallest additive fields.
3. Provide an idempotent SQLite `ALTER TABLE ... ADD COLUMN` compatibility
   step for existing databases.
4. Run the compatibility step before normal application use.
5. Preserve all existing rows and defaults.
6. Test both a fresh database and an existing Phase 3 database.

`Base.metadata.create_all()` must not be treated as an existing-table
migration mechanism.

### API impact

Preserve all existing endpoints and response fields.

Add one read-oriented endpoint:

```text
GET /api/intelligence/summary
```

The response should include:

- Ranked open issues and factor breakdowns.
- Related issue groups.
- Latest findings and recommendations with source IDs.
- Investigation states.
- Provenance and evidence IDs.
- Insufficient-data and provider-exhaustion warnings.
- Optional forecast data only when the gated enhancement is enabled.

Existing `POST /api/agents/runs` may receive an optional serializable context
field, but existing callers must remain valid. Existing monitoring endpoints
continue to use the same monitoring engine and executor.

No new blocking report-generation endpoint is required.

### Frontend impact

Extend the existing dashboard minimally:

- Add a Household intelligence section.
- Show ranked open issues and factor explanations.
- Group related issues across domains.
- Show linked findings, recommendations and investigation states.
- Show explicit insufficient-data and provider-exhaustion states.
- Preserve existing monitoring, chart, demo-seed and agent-analysis behavior.

No dashboard redesign or action-execution controls are included.

## 10. Implementation sequence and dependencies

### Phase 4A: Contracts and evidence context

1. Define serializable investigation-context schemas.
2. Define priority-factor and household-summary response schemas.
3. Identify the minimum related-issue selection rules.
4. Add context to the existing agent state and trace without changing the
   LangGraph topology.
5. Add focused schema and context tests.

Dependency: existing Phase 3 monitoring records and Phase 2 agent state.

### Phase 4B: Dynamic cross-agent reasoning

1. Build bounded context for a primary monitoring issue.
2. Include related open issues and deterministic evidence.
3. Extend Supervisor decisions to record context considered.
4. Ensure previous findings influence the next decision.
5. Preserve provider failover, exhaustion and budgets.
6. Add the energy-to-maintenance demonstration and contrast case.

Dependency: Phase 4A.

### Phase 4C: Prioritisation

1. Implement centralized ordinal factor mapping.
2. Implement lexicographic ranking and stable tie-breaking.
3. Compute priority for open issues and recommendations without arbitrary
   weights.
4. Add factor explanations and missing-evidence handling.
5. Add ranking tests with multiple domains and ties.

Dependency: existing monitoring schemas and evidence context.

### Phase 4D: Household report

1. Aggregate ranked issues, related issues, findings and recommendations.
2. Preserve issue/run provenance.
3. Add `GET /api/intelligence/summary`.
4. Add empty and seeded report behavior.
5. Add the minimal dashboard section.

Dependency: Phase 4B and Phase 4C.

### Phase 4E: Optional forecasting gate

1. Review essential test results and remaining complexity.
2. If safe, integrate only inventory depletion estimation.
3. Add evidence and confidence states.
4. Verify that forecasting cannot change issue lifecycle state.
5. Otherwise explicitly defer forecasting.

Dependency: all essential Phase 4 work.

### Phase 4F: Verification

1. Run targeted cross-agent, ranking and reporting tests.
2. Run the complete backend regression suite.
3. Run actual local API workflows on empty and seeded databases.
4. Run the frontend production build.
5. Verify the cross-domain demo through the running application.
6. Run `git diff --check`.
7. Update the Phase 3 report's stale test count and create the Phase 4
   implementation report only after verification.

## 11. Testing strategy and acceptance criteria

### Cross-agent tests

- Primary issue context contains only bounded, relevant related issues.
- Energy evidence can cause a Maintenance follow-up when supporting evidence
  exists.
- Energy without supporting maintenance evidence does not force Maintenance.
- Water-only investigations do not invoke unrelated specialists.
- Supervisor decisions record rationale and findings considered.
- Specialist selection is not asserted as a fixed global order.
- Investigation stops when evidence is sufficient.
- Supervisor and specialist budgets remain enforced.
- Provider exhaustion remains explicit.

### Prioritisation tests

- Each factor maps from documented evidence.
- Lexicographic ordering is stable and deterministic.
- Missing evidence lowers completeness/confidence.
- Missing evidence never fabricates severity or urgency.
- Ties resolve by stable fingerprint and detection time.
- Resolved issues do not appear in the open ranking.
- Recalculation reflects changed readings, inventory or appliance state.

### Reporting tests

- Multiple-domain issues appear in one household summary.
- Related issue groups preserve source issue IDs.
- Findings and recommendations retain source agent run IDs.
- Investigation status and provider exhaustion are visible.
- Empty database returns a valid empty summary.
- Seeded database preserves simulated labels.
- No unrelated findings are merged.

### Optional forecasting tests

If the gated enhancement is included:

- Sufficient inventory history returns a labelled estimate.
- Missing, zero-use or unstable history returns an insufficient-data state.
- Forecast output includes evidence count and confidence.
- Forecasts never create, resolve or reopen issues.

### Regression and local verification

- Existing backend tests continue to pass.
- Existing monitoring and provider tests continue to pass.
- Actual monitoring-triggering CRUD requests still return without waiting for
  agent completion.
- Manual monitoring continues to use the shared engine.
- Frontend production build passes.
- The running local application demonstrates the cross-domain workflow.
- No live provider claim is made unless credentials and provider availability
  are explicitly tested.

### Measurable acceptance criteria

Phase 4 is complete only when:

1. The existing Supervisor receives bounded primary and related issue context.
2. A previous specialist finding changes a later Supervisor decision in a
   tested end-to-end scenario.
3. No fixed specialist sequence or new agent is introduced.
4. Cross-domain selection records rationale and source evidence.
5. Existing budgets, provider failover and provider exhaustion behavior remain
   intact.
6. Open issues have deterministic, explainable priority factors.
7. Priority ordering uses documented lexicographic rules and stable ties.
8. Missing evidence lowers support rather than fabricating urgency or
   severity.
9. `GET /api/intelligence/summary` combines ranked issues, relationships,
   findings, recommendations and investigation states.
10. Every report finding and recommendation remains linked to source issue or
    agent-run IDs.
11. Empty and seeded databases produce valid, honest summaries.
12. Forecasting is either explicitly deferred or passes the optional evidence
    and lifecycle tests.
13. Existing APIs and Phase 1–3 workflows remain compatible.
14. Backend regression tests pass.
15. Frontend production build passes.
16. The local demo convincingly shows evidence-driven cross-agent reasoning.

## 12. Risks and mitigations

| Risk | Mitigation |
|---|---|
| Context becomes too large for providers | Include only the primary issue and a bounded number of related issues |
| Supervisor appears to follow a fixed sequence | Test positive and contrast cases; do not loop through all domains |
| Scores look arbitrary | Use documented ordinal factors and lexicographic ordering |
| Missing data creates false confidence | Preserve insufficient-data states and lower evidence completeness |
| Report duplicates unrelated findings | Require source issue/run IDs and explicit relationship rules |
| Existing SQLite data lacks new fields | Avoid schema changes; if required, use tested additive migration |
| Cross-domain runs duplicate investigations | Reuse Phase 3 transactional claims and bounded executor |
| Provider instability blocks the demo | Use mock mode for deterministic tests and preserve explicit exhaustion |
| Optional forecasting expands scope | Apply the Phase 4E gate and defer it without penalty |
| Existing Phase 1–3 behavior regresses | Run the full regression suite and local CRUD/monitoring workflows |

## 13. Explicit exclusions

- Sustainability Agent.
- Any new agent or separate Decision Engine.
- Fixed specialist execution pipeline.
- PostgreSQL, Redis, Kafka, Celery, n8n or message brokers.
- Complex machine-learning forecasting.
- Vector database or retrieval infrastructure.
- Autonomous consequential household actions.
- Notifications, approvals or external action execution.
- Telegram, computer vision or deployment work.
- Blocking LLM-only report generation.
- Broad rewrites of Phase 1–3 functionality.
- Unrelated frontend redesign.
- Production security, operations and environment hardening.

## 14. Phase 5 boundary

The following remain explicitly in Phase 5:

- Production deployment.
- Production environment configuration.
- Security hardening and secret-management review.
- Operational reliability and monitoring.
- Final documentation reconciliation.
- Final demo script and presentation preparation.
- Remaining UI polish.
- Any forecasting or reporting enhancements deferred by the Phase 4 gate.

Phase 4 must nevertheless provide a complete and convincing local
demonstration using the existing application architecture.
