"""Shared pytest fixtures."""

import os
import sys
from pathlib import Path

import pytest

BACKEND_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BACKEND_ROOT))
os.chdir(BACKEND_ROOT)


@pytest.fixture()
def tmp_db(tmp_path: Path):
    from app.core.db import Database

    return Database(str(tmp_path / "test_audit.db"))


@pytest.fixture()
def audit(tmp_db):
    from app.core.audit import AuditTrail

    return AuditTrail(tmp_db)
