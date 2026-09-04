"""Tests for configuration loading and test-mode enforcement."""

import pytest
from pydantic import ValidationError

from app.config import Settings


def test_settings_load_from_env_file() -> None:
    # .env exists in backend root (conftest chdir's there)
    s = Settings(_env_file=".env")
    assert s.razorpay_key_id.startswith("rzp_test_")
    assert s.razorpay_key_secret != ""
    assert s.database_url.startswith("sqlite:///")


def test_settings_defaults_without_env(tmp_path) -> None:
    s = Settings(_env_file=tmp_path / "does_not_exist.env")
    assert s.log_level == "INFO"
    assert "localhost:3000" in s.cors_origins


def test_live_key_is_rejected() -> None:
    with pytest.raises(ValidationError):
        Settings(
            razorpay_key_id="rzp_live_NOTALLOWED1234",
            razorpay_key_secret="whatever",
            _env_file=None,
        )


def test_sqlite_path_parsing() -> None:
    s = Settings(database_url="sqlite:///./some/dir/db.sqlite3", _env_file=None)
    assert s.sqlite_path == "./some/dir/db.sqlite3"


def test_credentials_configured_flag() -> None:
    assert Settings(razorpay_key_id="rzp_test_a", razorpay_key_secret="s", _env_file=None).credentials_configured
    assert not Settings(_env_file=None).credentials_configured
