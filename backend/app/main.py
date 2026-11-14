from __future__ import annotations

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app import clock
from app.config import get_settings
from app.db import initialize_database
from app.routers.household import router as household_router
from app.seed import seed_demo

settings = get_settings()
app = FastAPI(title="HomePilot AI", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origin_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.on_event("startup")
def on_startup() -> None:
    initialize_database()
    if settings.demo_autoseed:
        seed_demo()


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


app.include_router(household_router)


@app.post("/api/demo/seed")
def demo_seed() -> dict[str, int]:
    if not settings.feature_demo_panel:
        return {"created": 0}
    return seed_demo()


@app.post("/api/demo/advance-time")
def advance_time(days: int) -> dict[str, str]:
    if not settings.feature_demo_panel:
        return {"error": "Demo panel is disabled."}
    return {"now": clock.advance(days).isoformat()}
