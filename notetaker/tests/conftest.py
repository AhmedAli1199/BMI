import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
os.environ.update({"DATABASE_URL": "sqlite:///:memory:", "BOT_PROVIDER": "fake", "AI_PROVIDER": "fake", "ADMIN_TOKEN": "admin-t",
                   "INTERNAL_TOKEN": "int-t", "MAX_CONCURRENT_BOTS": "2", "ATTENDEE_WEBHOOK_SECRET": ""})

import pytest  # noqa: E402
from sqlalchemy import create_engine  # noqa: E402
from sqlalchemy.pool import StaticPool  # noqa: E402

from notetaker import db as dbmod  # noqa: E402


@pytest.fixture(autouse=True)
def fresh_db(monkeypatch):
    eng = create_engine("sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool)
    dbmod.SessionLocal.configure(bind=eng)
    dbmod.Base.metadata.drop_all(eng)
    dbmod.init_db(eng)
    from notetaker import providers
    providers.get_bot.cache_clear()
    providers.get_ai.cache_clear()
    yield eng


@pytest.fixture
def api():
    from fastapi.testclient import TestClient
    from notetaker.api.app import app
    return TestClient(app)


@pytest.fixture
def client_key(api):
    r = api.post("/admin/clients", json={"name": "BMI Brain", "webhook_url": "https://bmi.example.com/hook", "gemini_api_key": "bmi-own-key"}, headers={"X-Admin-Token": "admin-t"})
    assert r.status_code == 201, r.text
    return r.json()
