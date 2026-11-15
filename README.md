# HomePilot AI — Agentic AI Household Operations System

**HomePilot AI** is an autonomous, agentic AI-powered household operations and resource management system developed as a capstone project for the **IBM SkillsBuild Agentic AI Internship**, supporting UN Sustainable Development Goals (SDGs 7, 11, 12, and 13).

Rather than acting as a static dashboard or a single-prompt chatbot, HomePilot AI coordinates specialized agents dynamically using actual household telemetry and deterministic Python verification tools.

---

## Comprehensive Project Documentation

For an in-depth walkthrough of the system architecture, LangGraph multi-agent workflows, computer vision engine, database schemas, and end-to-end usage scenarios, see the complete documentation:

**[Read the Full Documentation](docs/HOMEPILOT_AI_COMPLETE_DOCUMENTATION.md)**

---

## Key Capabilities & Specialist Domains

HomePilot AI operates across four specialist domains:

1. **Energy Specialist**: Evaluates daily electricity consumption rates (`kWh/day`), compares against rolling 30-day baselines, and spots anomalies or seasonal spikes.
2. **Water Specialist**: Tracks water flow rates (`Litres/day`), executes leak signature heuristics, and flags continuous flow patterns.
3. **Maintenance Specialist**: Manages household appliance degradation, warranties, power ratings, and maintenance checklists.
4. **Inventory Specialist**: Monitors consumable supplies against safety reorder thresholds, tracks pantry quantities, and automatically populates household shopping lists.

### Advanced Multimodal Capabilities
- **Computer Vision-Based Inventory Scanning**: Uses multimodal AI to scan grocery receipts and pantry photos, performing fuzzy matching against existing pantry items with confidence scoring and audit logs.
- **Utility Bill Digitization & Analysis**: Digitizes paper and PDF electricity and water bills, extracts tariff breakdowns and consumption units, synchronizes with historical telemetry, and exports compliant RFC 4180 CSV files.

---

## Agentic Architecture

- **Dynamic LangGraph Supervisor**: Evaluates the user's objective and household evidence to select an appropriate specialist. It evaluates specialist tool findings and decides whether to hand off to another specialist or finalize recommendations.
- **Bounded Execution Budgets**: Prevents runaway LLM loops with strict limits on iteration depth (Supervisor budget: 8, Specialist budget: 5).
- **Deterministic Python Tools**: Mathematical and statistical telemetry computations are executed in deterministic Python tools (`energy_readings`, `water_readings`, `maintenance_statuses`, `inventory_levels`). LLMs do not invent math.
- **Staggered Provider Race & Failover**: Resilient multi-provider racing across Google Gemini, Groq, and OpenRouter with sanitized fallback and trace logging.
- **Continuous Monitoring Engine**: APScheduler runtime continuously executes periodic 15-minute scans and event-triggered evaluations with full provenance tracking.
- **Conversational Operational Assistant**: Natural-language chat grounded in real-time household data with the ability to trigger bounded multi-agent investigations.
- **Strict Household Isolation**: Authenticated sessions strictly partition all database telemetry, agent tool queries, investigations, and monitoring issues by `household_id`. Missing context fails closed.

---

## Tech Stack

- **Backend**: Python 3.11+, FastAPI, SQLAlchemy 2.0, APScheduler, LangGraph, Pydantic v2.
- **Database**: SQLite (local development) / PostgreSQL with `psycopg[binary]` (production).
- **Frontend**: React 18, Vite, Tailwind CSS, Recharts, Lucide Icons.
- **Deployment**: Render Blueprint (`render.yaml`) for FastAPI Web Service, React Static Site, and Managed PostgreSQL Database.

---

## Getting Started Locally

### Prerequisites

- Python 3.11+
- Node.js 18+
- (Optional) Google AI Studio API key, Groq API key, or OpenRouter API key

### 1. Backend Setup

```bash
# Navigate to backend directory
cd backend

# Create virtual environment (if not already created)
python -m venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Start backend server
uvicorn app.main:app --reload
```

API will be live at `http://localhost:8000`. Health check: `http://localhost:8000/api/health`.

Run backend tests:
```bash
# From backend directory
pytest tests -q
```

### 2. Frontend Setup

```bash
# Navigate to frontend directory
cd frontend

# Install dependencies
npm install

# Start Vite dev server
npm run dev
```

Frontend will be accessible at `http://localhost:5173`.

---

## Production Deployment on Render

The repository includes a complete Render Blueprint specification in `render.yaml`:

1. **`homepilot-api`**: FastAPI Python Web Service running on Python 3.13.
2. **`homepilot-web`**: React Static Site with client-side SPA routing rewrites.
3. **`homepilot-db`**: Managed PostgreSQL database.

### Deploying via Render Dashboard:
1. Push repository to GitHub.
2. In Render, select **New** -> **Blueprint**.
3. Connect your repository. Render automatically reads `render.yaml` and provisions the database, web service, and static site.
4. Set required secret environment variables (`GEMINI_API_KEY`, `OPENROUTER_API_KEY`, `GROQ_API_KEY`).

---

## Core API Endpoints

### Authentication & Household Isolation
- `POST /api/auth/register`: Create user account & isolated household.
- `POST /api/auth/login`: Authenticate and receive session token.
- `POST /api/auth/logout`: Invalidate session.
- `GET /api/auth/me` & `PATCH /api/auth/me`: Profile & theme settings.
- `GET /api/auth/household` & `PATCH /api/auth/household`: Household settings & onboarding status.
- `POST /api/auth/change-password`: Update account password.

### Household Telemetry & Specialist Domains
- `GET /api/dashboard/summary`: High-level operational metrics.
- `GET /api/readings?type=electricity|water`: List consumption records.
- `POST /api/readings`: Log new meter reading.
- `POST /api/readings/import`: Bulk import readings via CSV.
- `GET /api/appliances` & `POST /api/appliances`: Manage monitored appliances.
- `GET /api/inventory` & `POST /api/inventory`: Manage consumable supplies.
- `POST /api/inventory/scan-receipt`: Multimodal receipt/pantry scanner.
- `POST /api/inventory/receipt-suggestions/accept`: Apply scanned adjustments to inventory.
- `GET /api/inventory/logs`: Audit trail of inventory changes.
- `GET /api/bills` & `POST /api/bills/upload`: Ingest and list digitized utility bills.
- `GET /api/bills/{id}/csv`: Download RFC 4180 CSV export of bill.
- `GET /api/bills/trends`: Utility cost and tariff trend analytics.
- `GET /api/tasks` & `POST /api/tasks`: Manage maintenance tasks.
- `GET /api/shopping-list` & `POST /api/shopping-list`: Manage shopping items.

### Agentic Coordination & Monitoring
- `POST /api/agents/runs`: Launch LangGraph Supervisor investigation.
- `GET /api/agents/runs`: List historical investigation traces.
- `GET /api/agents/runs/{id}`: Detailed trace and candidate evaluations.
- `GET /api/monitoring/issues`: Active telemetry monitoring issues.
- `POST /api/monitoring/check`: Trigger manual monitoring sweep.
- `GET /api/intelligence/summary`: Prioritized issues, evidence-led recommendations, and cross-domain links.
- `POST /api/assistant/chat`: Converse with the grounded operational assistant.
- `GET /api/assistant/history`: Retrieve chat history.
- `DELETE /api/assistant/history`: Clear chat history.
- `POST /api/demo/seed`: Populate realistic demonstration telemetry strictly in current household.
