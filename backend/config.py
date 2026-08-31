"""
IntentGuard — Configuration Module

All environment variables and configurable thresholds.
No API keys may ever appear in frontend code or be committed to git.
"""

import os
from pathlib import Path
from pydantic_settings import BaseSettings
from pydantic import Field
from typing import Optional


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    # ── LLM Provider ──────────────────────────────────────────
    llm_provider: str = Field(default="gemini", description="LLM provider: 'gemini' or 'grok'")

    # ── Google Gemini ─────────────────────────────────────────
    gemini_api_key: Optional[str] = Field(default=None)
    gemini_model: str = Field(default="gemini-2.5-flash")

    # ── xAI Grok ──────────────────────────────────────────────
    xai_api_key: Optional[str] = Field(default=None)
    xai_model: str = Field(default="grok-3-mini")

    # ── Database ──────────────────────────────────────────────
    database_url: str = Field(default="sqlite+aiosqlite:///./intentguard.db")

    # ── Frontend URL (for CORS) ───────────────────────────────
    frontend_url: str = Field(default="http://localhost:3000")

    # ── API ───────────────────────────────────────────────────
    api_host: str = Field(default="0.0.0.0")
    api_port: int = Field(default=8000)

    # ── Confidence Thresholds ─────────────────────────────────
    confidence_threshold_high: float = Field(
        default=0.75,
        description="Confidence at or above this → ALLOW or BLOCK (depending on semantic judgment)"
    )
    confidence_threshold_low: float = Field(
        default=0.40,
        description="Confidence below this → ESCALATE (insufficient evidence)"
    )
    self_consistency_samples: int = Field(
        default=3,
        description="Number of semantic judgment samples for self-consistency"
    )

    # ── LLM Cost / Performance ────────────────────────────────
    llm_request_timeout: int = Field(default=30, description="LLM request timeout in seconds")
    llm_max_retries: int = Field(default=1, description="Max retries on LLM failure")

    # ── ML ────────────────────────────────────────────────────
    ml_enabled: bool = Field(default=True, description="Enable ML calibration layer")
    ml_model_path: str = Field(default="models/ambiguity_model.joblib")

    # ── Prompt Versions ───────────────────────────────────────
    extraction_prompt_version: str = Field(default="v1")
    semantic_prompt_version: str = Field(default="v1")
    explanation_prompt_version: str = Field(default="v1")

    # ── Paths ─────────────────────────────────────────────────
    @property
    def prompts_dir(self) -> Path:
        return Path(__file__).parent / "prompts"

    @property
    def data_cache_dir(self) -> Path:
        cache_dir = Path(__file__).parent / "data" / "cache"
        cache_dir.mkdir(parents=True, exist_ok=True)
        return cache_dir

    model_config = {
        "env_file": ".env",
        "env_file_encoding": "utf-8",
        "case_sensitive": False,
    }


# Singleton
_settings: Optional[Settings] = None


def get_settings() -> Settings:
    """Get or create the application settings singleton."""
    global _settings
    if _settings is None:
        _settings = Settings()
    return _settings


def reset_settings() -> None:
    """Reset settings (for testing)."""
    global _settings
    _settings = None
