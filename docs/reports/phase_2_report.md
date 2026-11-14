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
- The updated live configuration was loaded safely as `LLM_MODE=live` and `GEMINI_MODEL=gemini-3.8-flash`; the key was present but never printed.
- Installed provider versions are LangChain `0.3.27`, `langchain-google-genai` `2.1.12`, and LangGraph `0.6.10`.
- DNS, TCP 443 and HTTPS access to `generativelanguage.googleapis.com` succeeded.
- Authenticated model listing returned HTTP 200 and listed `gemini-3.8-flash` with `generateContent` and `countTokens` support.
- Authenticated `countTokens` returned HTTP 200.
- Minimal LangChain generation with a 30-second timeout and no retries returned gRPC `504 DEADLINE_EXCEEDED`.
- Direct REST `generateContent` with an 8-token limit timed out at 60 seconds and again at 120 seconds without an HTTP response.
- No quota, authentication or provider error response was returned for generation; this is a repeatable generation/request-latency timeout after successful connectivity and model-list checks.

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

- No live HomePilot agent workflow was run after the minimal generation failure.
- Electricity-spike, water-only, low-inventory, live decision-flow, live tool-call, live persistence and live recommendation claims remain unverified.
- `.env` was not modified and remains ignored/untracked.

## Known limitations

- Live generation needs further provider-side or client-transport investigation despite successful model listing and `countTokens`.
- Live model-dependent tests cannot be accepted while generation requests time out.
- Agent runs are stored as completed/stopped records; streaming, cancellation and retry handling are not implemented.
- Specialists perform no autonomous database writes.
- FastAPI and LangGraph emit non-blocking deprecation warnings.
- Telegram, vision, scheduling, n8n and deployment remain out of scope.

## Credentials and manual actions

- Investigate the provider generation timeout or transport/API compatibility before enabling live workflows.
- Keep `LLM_MODE=mock` for deterministic development and automated tests until generation completes reliably.

## Status

The genuine LangGraph orchestration correction is implemented and mock-verified. Live Gemini execution remains blocked by repeatable generation timeouts; Phase 2 is not fully verified and remains under review.
