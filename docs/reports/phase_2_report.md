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
- Added explicit Groq provider configuration for the existing Supervisor without changing the LangGraph topology or adding automatic failover.
- Added Groq JSON-schema decision validation with bounded reasoning (`low`), hidden reasoning output and a 1024-token completion budget.

## Verification

- Backend: `18 passed, 11 warnings` with `cd backend; python -m pytest tests -q` after the Groq integration.
- Focused provider/Supervisor tests: `9 passed, 11 warnings` after adding the Groq adapter.
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
- A minimal request using the recommended current `google-genai` `3.3.0` SDK and its default REST transport also returned sanitized HTTP `504 DEADLINE_EXCEEDED`; this reproduces the failure outside LangChain and gRPC.
- The diagnostic SDK environment was isolated to the project virtual environment and removed afterward. The project environment was restored to `pydantic 2.8.2`; `pip check` reported no broken requirements.
- Final installed diagnostic versions were `langchain-google-genai 2.1.12`, `google-ai-generativelanguage 0.12.1`, `grpcio 1.85.1`, `httpx 0.28.1`, `pydantic 2.8.2` and `tenacity 9.1.4`; `google-genai` is not a project dependency.
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
- The current SDK diagnostic did not run electricity-spike, water-only or low-inventory workflows because the required minimal generation gate failed.
- Electricity-spike, water-only, low-inventory, live decision-flow, live tool-call, live persistence and live recommendation claims remain unverified.
- `.env` was not modified and remains ignored/untracked.

## Groq integration results

- Groq model availability was verified separately for `openai/gpt-oss-20b` with HTTP 200.
- A corrected minimal Groq generation returned `READY` with HTTP 200 in 0.99 seconds.
- The Groq adapter and its Pydantic structured-decision parsing are covered by focused tests using a non-network fake response.
- A genuine Groq-powered Supervisor decision succeeded for an electricity-spike goal: it selected `energy`, returned a schema-valid decision, and completed in 1.02 seconds.
- One isolated end-to-end live workflow succeeded against temporary seeded SQLite data. It persisted the run, executed one deterministic energy tool, produced one finding, and made a subsequent Supervisor decision with `findings_seen` values `0, 1`. The Supervisor stopped without selecting maintenance because the returned evidence did not justify that follow-up; no recommendation was generated.
- The isolated workflow used `LLM_PROVIDER=groq` and `LLM_MODE=live` as process-local settings. The temporary database was removed after verification.

## Known limitations

- Live generation needs further provider-side investigation despite successful model listing and `countTokens`; the same failure was reproduced with LangChain/gRPC, direct REST and the current Google GenAI SDK.
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
