# Phase 2 correction report

## Implemented

- Replaced the fixed specialist loop with a real LangGraph `StateGraph` containing Supervisor, specialist and finalize nodes.
- Added LangChain structured decision models for live Gemini and a structured mock decision model using the same interface.
- Added bounded Energy, Water, Maintenance and Inventory specialists with separate deterministic Python toolsets.
- Added structured findings with category, subject, evidence, severity, confidence, explanations, next investigation and action.
- Enforced an 8-call Supervisor budget and 5-call-per-specialist tool budget; exhaustion is terminal and recorded.
- Added persisted findings, decisions, budgets, stop reasons, tool results and recommendation traces.
- Added recommendation scoring, valid finding references and duplicate suppression.
- Preserved `POST /api/agents/runs` and `GET /api/agents/runs/{run_id}`.
- Updated the dashboard to render structured recommendation subjects, actions and scores.
- Added behavioral tests for dynamic routing, evidence flow, water-only and inventory-only scope, insufficient history, irrelevant goals, budget exhaustion and suppression.

## Verification

- Backend: `16 passed, 11 warnings` with `cd backend; python -m pytest tests -q`.
- Focused graph tests verify that later decisions receive prior findings (`findings_seen`), rather than asserting a fixed trace.
- Frontend: `npm run build --prefix frontend` passed. Vite emitted its existing non-blocking bundle-size advisory.
- Pylance import audit is clean for LangChain/Gemini imports after installation.
- Root `.env` exists, is loaded by backend configuration, is ignored by Git, and is not tracked. Secret values were never printed or committed.
- Configured live Gemini model check failed with HTTP 404: `gemini-2.5-flash` is no longer available to new users; the provider recommends `gemini-3.8-flash`.
- A live invocation with the provider-recommended `gemini-3.8-flash` override was attempted without modifying `.env`; it exceeded the local 220-second command window without a response and was stopped.

## Mock mode results

- Full LangGraph topology executes in mock mode.
- Different goals produce different initial specialist decisions.
- Findings drive follow-up maintenance investigation after an electricity spike.
- Water-only and inventory-only goals do not invoke unrelated specialists.
- Insufficient history produces an evidence-limited finding and requests additional readings.
- Irrelevant goals stop without specialist tool calls.
- Supervisor and specialist budget exhaustion are terminal and trace-recorded.
- Recommendations reference valid finding IDs and duplicate proposals are suppressed.

## Live Gemini results

- The root `.env` key was detected without exposing it.
- The configured `gemini-2.5-flash` model reached the provider but returned HTTP 404 because it is unavailable to new users. The provider response recommended `gemini-3.8-flash`.
- `.env` was not changed. The provider-recommended `gemini-3.8-flash` was tested only as a process-level override and did not complete within the test window.
- The override invocation did not complete within the test window, so no live Gemini workflow is declared successful.

## Known limitations

- The configured model must be changed manually in `.env` to a provider-supported model before normal live mode can work.
- Live model-dependent tests cannot be accepted while the configured model returns 404.
- Agent runs are stored as completed/stopped records; streaming, cancellation and retry handling are not implemented.
- Specialists perform no autonomous database writes.
- FastAPI and LangGraph emit non-blocking deprecation warnings.
- Telegram, vision, scheduling, n8n and deployment remain out of scope.

## Credentials and manual actions

- Set `GEMINI_MODEL` in the root `.env` to a model available to the account, following the provider's recommendation.
- Keep `LLM_MODE=mock` for deterministic development and automated tests until the model is corrected.

## Status

The genuine LangGraph orchestration correction is implemented and mock-verified. Live Gemini execution remains blocked by the configured model's provider 404; Phase 2 should remain under review until a supported model is configured and a real workflow succeeds.
