# HomePilot AI architecture

## Target architecture

FastAPI exposes household data APIs and agent/run APIs. SQLAlchemy persists SQLite records. Pure domain functions perform all arithmetic and date logic. LangGraph provides bounded Supervisor and specialist routing, while LangChain Gemini structured output supplies live Supervisor decisions. React/Vite presents charts, data entry and trace/recommendation pages. Optional Telegram, vision, n8n and deployment integrations are feature-flagged.

## As-built architecture after Phase 2

FastAPI starts the application, initializes SQLAlchemy tables, and optionally seeds simulated demo data. The current API supports readings, appliances, inventory with append-only quantity logs, shopping-list items, tasks, dashboard summary, CSV import, and demo time/seed endpoints. The React app renders the dashboard, consumption charts and persisted household-analysis findings/recommendations. The agent layer uses a LangGraph Supervisor loop, bounded Energy/Water/Maintenance/Inventory specialists, deterministic Python tools, structured findings, budget enforcement and recommendation suppression. Mock mode uses the same graph with a structured evidence-aware decision model; live mode uses LangChain Gemini when the configured model is supported.
