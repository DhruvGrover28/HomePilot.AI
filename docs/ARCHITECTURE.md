# HomePilot AI architecture

## Target architecture

FastAPI exposes household data APIs and later agent/run APIs. SQLAlchemy persists SQLite records. Pure domain functions perform all arithmetic and date logic. LangGraph and Gemini will be added in Phase 2 for bounded Supervisor and specialist routing. React/Vite presents charts, data entry and later trace/recommendation pages. Optional Telegram, vision, n8n and deployment integrations are feature-flagged.

## As-built architecture after Phase 2

FastAPI starts the application, initializes SQLAlchemy tables, and optionally seeds simulated demo data. The current API supports readings, appliances, inventory with append-only quantity logs, shopping-list items, tasks, dashboard summary, CSV import, and demo time/seed endpoints. The React app renders the dashboard, consumption charts and persisted household-analysis recommendations. The agent layer currently uses a deterministic Supervisor and specialist functions in mock mode; no LLM or external integration is enabled yet.
