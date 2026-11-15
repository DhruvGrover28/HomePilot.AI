from functools import lru_cache
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict

PROJECT_ROOT = Path(__file__).resolve().parents[2]


class Settings(BaseSettings):
    database_url: str = "sqlite:///./homepilot.db"
    cors_origins: str = "http://localhost:5173"
    llm_mode: str = "mock"
    llm_provider: str = "gemini"
    gemini_api_key: str = ""
    gemini_model: str = ""
    groq_api_key: str = ""
    groq_model: str = "openai/gpt-oss-20b"
    openrouter_api_key: str = ""
    openrouter_model: str = "anthropic/claude-sonnet-5.5"
    llm_provider_order: str = "openrouter,groq,gemini"
    feature_telegram: bool = False
    feature_vision: bool = False
    feature_followups: bool = True
    feature_demo_panel: bool = True
    demo_autoseed: bool = False
    electricity_tariff_per_kwh: float | None = None
    water_tariff_per_kl: float | None = None
    grid_emission_factor_kg_per_kwh: float = 0.71
    stale_reading_days: int = 35
    warranty_warn_days: int = 30
    stockout_warn_days: int = 7
    monitoring_enabled: bool = True
    monitoring_interval_minutes: int = 15
    monitoring_max_workers: int = 2
    monitoring_max_pending_jobs: int = 4
    monitoring_claim_timeout_minutes: int = 30
    session_cookie_secure: bool = False
    session_cookie_samesite: str = "lax"

    model_config = SettingsConfigDict(env_file=PROJECT_ROOT / ".env", extra="ignore")

    @property
    def cookie_secure(self) -> bool:
        return self.session_cookie_secure

    @property
    def cookie_samesite(self) -> str:
        val = (self.session_cookie_samesite or "lax").strip().lower()
        if val not in {"lax", "strict", "none"}:
            return "lax"
        return val

    @property
    def cors_origin_list(self) -> list[str]:
        return [origin.strip() for origin in self.cors_origins.split(",") if origin.strip()]

    @property
    def llm_provider_order_list(self) -> list[str]:
        providers = [provider.strip().lower() for provider in self.llm_provider_order.split(",") if provider.strip()]
        if not providers or any(provider not in {"gemini", "groq", "openrouter"} for provider in providers):
            raise ValueError("LLM_PROVIDER_ORDER must contain only gemini, groq, and openrouter.")
        return providers


@lru_cache
def get_settings() -> Settings:
    return Settings()
