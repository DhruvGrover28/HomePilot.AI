# Existing codebase decisions

The read-only Phase 0 audit found a small finance-oriented prototype:

- The FastAPI/Vite repository scaffold, CORS setup, startup hook, and local development conventions are reusable.
- The frontend React/Tailwind build setup is reusable.
- The old transaction schema, expense router, CSV parser, expense service, expense agent, prompt, and finance dashboard are not reusable for HomePilot and are replaced by Phase 1.
- No files are deleted in Phase 1; the pre-rework state is preserved by the `pre-homepilot-rework` tag.
- The new application uses SQLAlchemy with SQLite and a versioned initialization module (`create_all` for this prototype).
