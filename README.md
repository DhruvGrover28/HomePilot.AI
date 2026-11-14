# HomePilot AI

HomePilot AI is an autonomous household operations manager built for IBM SkillsBuild internship submission goals tied to SDGs 7, 11, 12, and 13.

Phase 1 includes the household foundation: SQLite household records, validated reading CSV import, deterministic demo seeding, consumption charts, and CRUD APIs for readings, appliances, inventory, shopping lists and tasks. Agentic features are planned for later phases.

## Repository Structure

- frontend/
- backend/
- n8n/
- docs/
- CHANGELOG.md

## Tech Stack in Phase 1

- Frontend: React plus Tailwind CSS (Vite)
- Backend: FastAPI (Python)
- Database: SQLite via SQLAlchemy

## Prerequisites

- Node.js 18+
- Python 3.11+
- Google AI Studio API key

## Environment Variables

Backend: copy `.env.example` to `.env` if configuration overrides are needed. Phase 1 defaults to mock/offline mode.

Frontend (create frontend/.env locally):
- VITE_API_BASE_URL=http://localhost:8000

## Local Run

### Backend

1. Install dependencies:
   pip install -r backend/requirements.txt
2. Start API:
   uvicorn app.main:app --reload --app-dir backend
3. Health check:
   GET http://localhost:8000/health

Run backend tests from the backend module root:

   cd backend
   python -m pytest tests -q

### Frontend

1. Install dependencies:
   npm install --prefix frontend
2. Run development server:
   npm run dev --prefix frontend
3. Open local URL shown by Vite.

## API

Key endpoints include `GET /api/dashboard/summary`, CRUD endpoints under `/api/readings`, `/api/appliances`, `/api/inventory`, `/api/shopping-list`, and `/api/tasks`, `POST /api/readings/import`, `POST /api/demo/seed`, `POST /api/agents/runs`, and `GET /api/agents/runs/{run_id}`.

Phase 2 agent analysis uses a bounded LangGraph Supervisor. `LLM_MODE=mock` runs the same graph offline with structured mock decisions. In live mode, explicit selection uses `LLM_PROVIDER=gemini`, `groq`, or `openrouter`; `LLM_PROVIDER=auto` runs a staggered provider race using the configured `LLM_PROVIDER_ORDER` (default `openrouter,groq,gemini`) at each Supervisor decision. OpenRouter starts immediately, Groq starts after 10 seconds, and Gemini starts after 20 seconds; the shared race deadline is 50 seconds. It never silently switches to mock mode. Configure the selected provider with its API key and model:

- Gemini: `GEMINI_API_KEY` and `GEMINI_MODEL`
- Groq: `GROQ_API_KEY` and `GROQ_MODEL` (default `openai/gpt-oss-20b`)
- OpenRouter: `OPENROUTER_API_KEY` and `OPENROUTER_MODEL` (default `anthropic/claude-sonnet-5.5`)

Fallback is limited to provider connection/timeout, rate-limit, server-unavailability, configuration, empty-response and structured-schema failures. Programming errors and valid Supervisor stop decisions do not trigger fallback. Started providers run concurrently; the first valid Pydantic decision wins, while remaining tasks are cancelled on a best-effort basis without waiting for losing requests. Each attempt is recorded in the persisted trace with scheduled/actual start, elapsed time, outcome, cancellation, winner status, failure category and HTTP status where available. If all configured providers fail or the shared deadline expires, the run stops with a sanitized provider-exhaustion event and no specialist tool is executed.

OpenRouter's `anthropic/claude-sonnet-5.5` model may be routed internally to a hosting provider such as Azure. That internal route is distinct from HomePilot's application-level OpenRouter → Groq → Gemini provider race.

## Deployment Plan for Phase 1

- Frontend: Vercel free tier
- Backend: Render free tier
- Render Python version: 3.13.14

Deployment status currently pending based on your instruction to complete account project setup after Phase 1 coding.

If Render defaults to Python 3.14, keep backend/runtime.txt in place so the backend service uses Python 3.13.14 instead of compiling unsupported wheels from source.

## Phase 3 Advance Note

n8n will be self-hosted on Render free tier. Free tier instances may cold start after inactivity, which can delay webhook and scheduled flow execution.

## Manual Test Checklist (Phase 1)

1. Start backend and frontend locally.
2. Upload backend/tests/sample_bank_statement.csv from dashboard.
3. Verify categorized transactions are shown.
4. Verify anomalies appear (duplicate and or unusually large).
5. Confirm upload API returns non-empty upload_id.

## Live Links

Pending creation after Phase 1 code completion and hosting setup:
- Frontend URL: pending
- Backend URL: pending
