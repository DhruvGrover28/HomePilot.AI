# Phase 2 correction plan

## Scope

- Implement a LangGraph Supervisor loop with structured model decisions.
- Route dynamically to bounded Energy, Water, Maintenance and Inventory specialists.
- Give each specialist deterministic Python tools and structured findings.
- Enforce supervisor and specialist tool budgets and record every decision/tool result.
- Persist completed agent runs with findings, decisions, recommendations and traces.
- Keep the same topology in `LLM_MODE=mock` through a structured mock decision model.
- Use LangChain Gemini structured output for live Supervisor decisions.
- Add a dashboard action that displays findings, recommendations and routing.

## Explicitly out of scope

- Live Gemini calls with the configured model when provider validation succeeds.
- Telegram, vision, scheduling, n8n and deployment.
- Autonomous writes to household records.

## Verification

1. Run the complete backend pytest suite, including dynamic routing and budget cases.
2. Run the frontend production build.
3. Exercise mock agent runs over live HTTP with an isolated SQLite database.
4. Exercise empty and seeded analysis from the running browser application.
5. Test the configured Gemini model and record provider/authentication results without exposing credentials.
6. Record exact results in the Phase 2 report, update changelogs, commit and push.
