from __future__ import annotations

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app import clock
from app.config import get_settings
from app.db import initialize_database
from app.routers.household import router as household_router
from app.routers.agents import router as agents_router
from app.routers.monitoring import router as monitoring_router
from app.seed import seed_demo
from app.services.monitoring_runtime import monitoring_runtime

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
    monitoring_runtime.start()
    if settings.demo_autoseed:
        seed_demo()


@app.on_event("shutdown")
def on_shutdown() -> None:
    monitoring_runtime.stop()


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


app.include_router(household_router)
app.include_router(agents_router)
app.include_router(monitoring_router)


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
