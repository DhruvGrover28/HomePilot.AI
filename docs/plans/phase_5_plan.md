# Phase 5 Plan: Product Finalisation, Security and Deployment

## Status: Completed (Verified)

All Phase 5 requirements (Phases 5A through 5H) have been fully implemented and verified:
- End-to-end security and household isolation active across all APIs, LangGraph Supervisor, specialist tools, and monitoring.
- Modular React SaaS architecture with responsive navigation, 4 specialist views (Energy, Water, Maintenance, Inventory), Monitoring, Investigations, Assistant, and Settings.
- Onboarding wizard and public landing page with interactive authentication.
- Grounded conversational assistant with investigation links.
- Render deployment blueprint (`render.yaml`) and PostgreSQL production engine support (`psycopg[binary]`).
- Full test suite passing (64 tests, 0 failures) and frontend production build passing cleanly.

## 1. Current-state audit

### Existing

- FastAPI backend with SQLite, SQLAlchemy and existing household CRUD APIs.
- LangGraph Supervisor with Energy, Water, Maintenance and Inventory
  specialists.
- Gemini, Groq and OpenRouter orchestration with bounded budgets and explicit
  provider exhaustion.
- Scheduled, event-driven and manual monitoring with bounded investigations.
- Deterministic household intelligence and `GET /api/intelligence/summary`.
- React dashboard with monitoring, analysis, charts and intelligence sections.
- Mock-mode workflows suitable for deterministic demonstrations.

### Missing

- Authentication, accounts and backend authorization.
- User and household ownership isolation.
- First-time onboarding and authenticated route structure.
- Public landing page and cohesive responsive application shell.
- Profile, appearance and household settings.
- Investigation detail/activity presentation.
- Conversational assistant using the existing Supervisor and specialists.
- Repeatable demo reset and final deployment configuration.
- Production migration, security and operational documentation.

### Constraints

- No fifth specialist, fixed investigation pipeline or autonomous household
  actions.
- No sharing, invitations, roles, Redis, Celery, Kafka, vector database or
  unnecessary paid service.
- Do not claim IoT integration, live telemetry, password recovery or live LLM
  success unless verified.

## 2. Implementation sequence

### Phase 5A: Audit and closure

1. Keep the Phase 4 report accurate: 57 backend tests, frontend build and API
   smoke checks passed; live cross-agent execution remains unverified because
   of provider rate limiting.
2. Correct historical Phase 3 test-count documentation without rewriting its
   scope.
3. Verify provider cancellation behavior with controlled tests.

### Phase 5B: Database, authentication and ownership

1. Add additive SQLite migrations for users, households, sessions and ownership
   fields; never rely on `create_all()` to alter existing tables.
2. Implement secure password hashing, HTTP-only session cookies, expiry,
   logout and protected backend dependencies.
3. Associate household records and background investigations with the
   authenticated household.
4. Add authorization tests proving cross-household reads, writes, monitoring,
   runs and conversations are rejected.
5. Keep password reset deferred unless a secure delivery mechanism is approved.

### Phase 5C: Onboarding and design system

1. Add a welcome-to-completion onboarding flow for household details, assets,
   inventory and optional historical data.
2. Add explicit simulated/manual data labels.
3. Establish responsive shell, typography, theme, loading, empty and error
   states using existing frontend dependencies.

### Phase 5D: Public and authenticated frontend

1. Add public landing page with accurate features and agentic architecture.
2. Add registration, login, logout and protected application routes.
3. Redesign dashboard progressively without breaking existing workflows.
4. Add profile, settings, household and appearance screens.

### Phase 5E: Agentic experience

1. Add investigation list/detail views using persisted decisions, findings,
   provider attempts, context relationships and lifecycle status.
2. Add an activity centre based on persisted monitoring and investigation data.
3. Add a conversational assistant endpoint that reuses the existing Supervisor
   and specialists, limits context to the authenticated household and never
   writes directly to the database.
4. Use ordinary request/response behavior first; do not introduce streaming
   infrastructure without a demonstrated need.

### Phase 5F: Demonstration and reliability

1. Provide a repeatable, scoped demo household seed/reset.
2. Demonstrate Energy evidence, dynamic Maintenance selection, findings,
   deterministic relationships and recommendations in mock mode.
3. Verify empty, seeded, authenticated, unauthorized, provider-exhausted and
   interrupted-investigation states.

### Phase 5G: Deployment readiness

1. Add safe production migration commands and startup checks.
2. Prepare Render-compatible frontend/backend configuration without committing
   secrets or provisioning paid services.
3. Configure explicit CORS, secure cookies, trusted hosts and production
   logging.
4. Document SQLite limitations and the point at which a managed database would
   be required.

### Phase 5H: Final polish

1. Run accessibility, build, regression, API and deployment-readiness checks.
2. Update changelog, reports, README and demo instructions only for verified
   behavior.
3. Prepare the final presentation and known-limitations report.

## 3. Dependencies and migration policy

Authentication and ownership precede protected frontend routes, onboarding,
background household execution and conversations. Additive migrations must
preserve existing local data and include a rollback or backup explanation.
Existing unauthenticated development behavior may remain behind an explicit
mock/development setting, but production routes must require authentication.

## 4. Acceptance criteria

- Users can register, log in, log out and access only their household data.
- Passwords are hashed and sessions use secure server-managed cookies.
- Cross-household API access is rejected, including background monitoring and
  agent investigations.
- A new user completes onboarding without misleading empty dashboard claims.
- Public landing and authenticated application routes are responsive and
  accessible.
- Existing monitoring, intelligence, agent and CRUD behavior remains intact.
- Investigation detail views expose actual Supervisor decisions and findings.
- The assistant reuses the existing agent architecture and cannot mutate data.
- Mock mode provides a repeatable demo when providers are unavailable.
- Empty, seeded, unauthorized, provider-exhausted and interrupted states are
  tested and honestly represented.
- Frontend production build, backend tests, migration checks and API smoke
  tests pass.
- Deployment configuration is ready without secrets or unapproved paid
  services.

## 5. Explicitly deferred or excluded

- Household sharing, invitations, multi-user roles and administration.
- Fifth specialist or competing decision engine.
- Autonomous physical actions, notifications and consequential automation.
- IoT integrations not present in the implementation.
- Email/SMS/Telegram/push infrastructure unless separately approved.
- Complex ML, vector search, distributed workers and unnecessary infrastructure.
- Password recovery until secure credential delivery is available.
