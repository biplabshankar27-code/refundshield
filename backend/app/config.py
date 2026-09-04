"""RefundShield configuration.

Keys are read ONLY from environment variables / a local .env file
(never hardcoded, never committed). Razorpay LIVE keys are rejected —
this system is TEST MODE only.
"""

from functools import lru_cache
from pathlib import Path

from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # --- Razorpay Test Mode credentials (from environment / .env) ---
    razorpay_key_id: str = ""
    razorpay_key_secret: str = ""

    # --- Storage ---
    database_url: str = "sqlite:///./refundshield.db"

    # --- App behaviour ---
    refundsield_env: str = "development"
    log_level: str = "INFO"
    cors_origins: str = "http://localhost:3000"

    # Regex for dynamic origins (e.g. Vercel preview/prod URLs, local dev
    # ports). Empty string disables. Default covers *.vercel.app plus any
    # localhost port.
    cors_origin_regex: str = (
        r"^(https://[a-z0-9-]+\.vercel\.app|http://localhost:\d+)$"
    )

    # Optional: webhook signing secret for /api/webhooks/razorpay
    razorpay_webhook_secret: str = ""

    @field_validator("razorpay_key_id")
    @classmethod
    def enforce_test_mode(cls, v: str) -> str:
        """Defense in depth: refuse LIVE keys at config level."""
        if v and not v.startswith("rzp_test_"):
            raise ValueError(
                "RefundShield is TEST MODE only: RAZORPAY_KEY_ID must start with "
                f"'rzp_test_' (got '{v[:12]}...')."
            )
        return v

    @property
    def cors_origin_list(self) -> list[str]:
        return [o.strip() for o in self.cors_origins.split(",") if o.strip()]

    @property
    def sqlite_path(self) -> str:
        """Extract a filesystem path from a sqlite:///. DATABASE_URL."""
        url = self.database_url
        if url.startswith("sqlite:///"):
            path = url[len("sqlite:///"):]
            return path or "refundshield.db"
        if url.startswith("sqlite:"):
            return url[len("sqlite:"):] or "refundshield.db"
        return url

    @property
    def credentials_configured(self) -> bool:
        return bool(self.razorpay_key_id and self.razorpay_key_secret)


@lru_cache
def get_settings() -> Settings:
    """Cached settings accessor (safe to call per-request via FastAPI Depends)."""
    return Settings()
