# HomePilot AI

HomePilot AI is an autonomous household operations manager built for IBM SkillsBuild internship submission goals tied to SDGs 7, 11, 12, and 13.

Phase 1 includes an end-to-end proof of concept:
- Upload a bank statement CSV.
- Parse and store transactions in SQLite.
- Run the Expense Agent to categorize transactions and flag anomalies.
- View categorized transactions and anomalies on a React dashboard.

## Repository Structure

- frontend/
- backend/
- n8n/
- docs/
- CHANGELOG.md

## Tech Stack in Phase 1

- Frontend: React plus Tailwind CSS (Vite)
- Backend: FastAPI (Python)
- Agent: LangChain chain with Google Gemini
- Database: SQLite

## Prerequisites

- Node.js 18+
- Python 3.11+
- Google AI Studio API key

## Environment Variables

Backend (create backend/.env locally):
- GEMINI_API_KEY=your_key_here

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

### Frontend

1. Install dependencies:
   npm install --prefix frontend
2. Run development server:
   npm run dev --prefix frontend
3. Open local URL shown by Vite.

## API

- POST /api/expenses/upload
  - multipart/form-data with file field (CSV only)
  - Returns upload_id, categorized transactions, and anomaly counts

Expected CSV headers:
- date
- description
- amount
- merchant (optional)

## Deployment Plan for Phase 1

- Frontend: Vercel free tier
- Backend: Render free tier

Deployment status currently pending based on your instruction to complete account project setup after Phase 1 coding.

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
