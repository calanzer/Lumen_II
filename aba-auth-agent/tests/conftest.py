"""Shared fixtures: a fresh API app with a throwaway database and the AI steps stubbed."""

import json
import os
from pathlib import Path

import bcrypt
import pytest
import yaml
from fastapi.testclient import TestClient

from schemas.clinical_data import ExtractedClinicalData
from schemas.narrative import AnthemReauthNarrative

FIXTURES = Path(__file__).parent / "fixtures"
TEST_DB_PATH = FIXTURES / "test_api.db"


def _hash(password: str) -> str:
    return bcrypt.hashpw(password.encode(), bcrypt.gensalt(rounds=4)).decode()


@pytest.fixture
def app(monkeypatch, tmp_path):
    """A fresh app with a throwaway database, two users, and the AI steps stubbed."""
    config = tmp_path / "auth_config.yaml"
    config.write_text(
        yaml.dump(
            {
                "credentials": {
                    "usernames": {
                        "tester": {"name": "Test BCBA", "password": _hash("pw-123")},
                        "other": {"name": "Other BCBA", "password": _hash("pw-456")},
                    }
                },
                "cookie": {"name": "c", "key": "test-signature-key", "expiry_days": 1},
            }
        )
    )
    monkeypatch.setattr("auth_config.AUTH_CONFIG_PATH", config)
    monkeypatch.setattr("data.store.DB_PATH", TEST_DB_PATH)

    import api.auth as auth
    import api.imports as imports

    auth._failures.clear()
    imports.JOBS.clear()

    with open(FIXTURES / "realistic_extraction.json") as f:
        raw = json.load(f)
    raw["client"].update(
        {"client_id": "HB-100", "payor_name": "Aetna", "auth_period_start": "2026-01-01", "auth_period_end": "2026-06-30"}
    )
    state = {"raw": raw, "fail_extract": None, "fail_draft": None, "fail_check": None}

    def fake_extract(file_bytes, filename):
        if state["fail_extract"]:
            raise RuntimeError(state["fail_extract"])
        return ExtractedClinicalData.model_validate(state["raw"])

    def fake_draft(data, payor_key):
        if state["fail_draft"]:
            raise RuntimeError(state["fail_draft"])
        with open(FIXTURES / "realistic_narrative.json") as f:
            narrative = AnthemReauthNarrative.model_validate(json.load(f))
        # the real drafting step records which data it was written from
        from pipeline.intake import source_hash

        narrative.source_hash = source_hash(data)
        return narrative

    def fake_check(narrative, data):
        if state["fail_check"]:
            raise RuntimeError(state["fail_check"])
        return ["[S] Claim: x (value: 9) — could not trace 9 to the source data. Verify manually."]

    monkeypatch.setattr(imports.hooks, "extract", fake_extract)
    monkeypatch.setattr(imports.hooks, "draft", fake_draft)
    monkeypatch.setattr(imports.hooks, "check", fake_check)

    from api.main import create_app

    with TestClient(create_app()) as client:
        client.state = state
        yield client
    for suffix in ("", "-wal", "-shm"):
        extra = Path(str(TEST_DB_PATH) + suffix)
        if extra.exists():
            os.remove(extra)
