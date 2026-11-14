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

    model_config = SettingsConfigDict(env_file=PROJECT_ROOT / ".env", extra="ignore")

    @property
    def cors_origin_list(self) -> list[str]:
        return [origin.strip() for origin in self.cors_origins.split(",") if origin.strip()]


@lru_cache
def get_settings() -> Settings:
    return Settings()
