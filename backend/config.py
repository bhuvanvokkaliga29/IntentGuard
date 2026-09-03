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

    # ── Razorpay ──────────────────────────────────────────────
    razorpay_key_id: Optional[str] = Field(default=None, description="Razorpay API Key ID")
    razorpay_key_secret: Optional[str] = Field(default=None, description="Razorpay API Key Secret")
    razorpay_enabled: bool = Field(default=True, description="Enable Razorpay financial execution adapter")

    # ── Database ──────────────────────────────────────────────
    database_url: str = Field(
        default="sqlite+aiosqlite:///./intentguard.db",
        description="Database URL (SQLite for dev, PostgreSQL for prod e.g. postgresql+asyncpg://...)"
    )

    # ── Async Queue & Redis (Production) ──────────────────────
    redis_url: Optional[str] = Field(
        default=None,
        description="Redis broker URL for asynchronous task queue (e.g., redis://localhost:6379/0)"
    )

    # ── Environment & Observability ───────────────────────────
    environment: str = Field(default="development", description="'development', 'staging', or 'production'")
    log_format: str = Field(default="json", description="Structured log format: 'json' or 'text'")
    prometheus_enabled: bool = Field(default=True, description="Enable Prometheus metrics at /metrics")
    otlp_endpoint: Optional[str] = Field(default=None, description="OpenTelemetry / centralized collector endpoint")

    # ── Frontend URL (for CORS) ───────────────────────────────
    frontend_url: str = Field(default="http://localhost:3000")

    # ── API ───────────────────────────────────────────────────
    api_host: str = Field(default="0.0.0.0")
    api_port: int = Field(default=8000)
    submission_track: str = Field(default="Track 5 — Open Track", description="Hackathon submission track")

    # ── Security & Authentication ──────────────────────────────
    api_key: Optional[str] = Field(default=None, description="API Key for protected endpoints (None = dev open mode)")
    rate_limit_enabled: bool = Field(default=True, description="Enable request rate limiting")
    rate_limit_per_minute: int = Field(default=120, description="Max requests per minute per IP")

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

    # ── Agent Runtime ──────────────────────────────────────────
    agent_max_runtime_seconds: int = Field(default=120, description="Hard timeout for agent pipeline execution in seconds")

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

def fetch_aws_secrets(secret_name: str, region_name: str = "us-east-1") -> dict:
    """Fetch secrets from AWS Secrets Manager."""
    try:
        import boto3
        import json
        from botocore.exceptions import ClientError
        
        session = boto3.session.Session()
        client = session.client(
            service_name='secretsmanager',
            region_name=region_name
        )
        get_secret_value_response = client.get_secret_value(SecretId=secret_name)
        if 'SecretString' in get_secret_value_response:
            return json.loads(get_secret_value_response['SecretString'])
        return {}
    except ImportError:
        return {}
    except Exception as e:
        print(f"Failed to fetch secrets from AWS: {e}")
        return {}

def get_settings() -> Settings:
    """Get or create the application settings singleton."""
    global _settings
    if _settings is None:
        _settings = Settings()
        
        # Override with AWS Secrets if enabled
        if os.environ.get("AWS_SECRETS_MANAGER_ENABLED", "false").lower() == "true":
            secret_name = os.environ.get("AWS_SECRET_NAME", "intentguard-secrets")
            aws_secrets = fetch_aws_secrets(secret_name)
            
            if "GEMINI_API_KEY" in aws_secrets:
                _settings.gemini_api_key = aws_secrets["GEMINI_API_KEY"]
            if "XAI_API_KEY" in aws_secrets:
                _settings.xai_api_key = aws_secrets["XAI_API_KEY"]
            if "DATABASE_URL" in aws_secrets:
                _settings.database_url = aws_secrets["DATABASE_URL"]
                
    return _settings


def reset_settings() -> None:
    """Reset settings (for testing)."""
    global _settings
    _settings = None
