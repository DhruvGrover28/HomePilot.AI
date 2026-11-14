# Demo script

## Phase 1 foundation

1. Start the backend with `uvicorn app.main:app --reload --app-dir backend`.
2. Start the frontend with `npm run dev --prefix frontend` from a shell that supports the frontend working directory.
3. Use **Seed simulated demo** in the dashboard.
4. Confirm the electricity and water charts render, appliances show simulated badges, and summary counts update.
5. Upload a CSV to `POST /api/readings/import` containing a malformed row and confirm the response identifies the exact row without importing any rows.

The dynamic investigation, proactive monitoring and closed-loop scenarios are intentionally deferred to Phases 2 and 3.
