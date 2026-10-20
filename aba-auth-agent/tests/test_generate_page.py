"""Regression tests for the Generate page's editable narrative sections."""

import json
import os
from pathlib import Path

import pytest
from streamlit.testing.v1 import AppTest

from schemas.clinical_data import ExtractedClinicalData
from schemas.narrative import TemplateSection

FIXTURES = Path(__file__).parent / "fixtures"
TEST_DB_PATH = FIXTURES / "test_generate_page.db"


@pytest.fixture
def seeded(monkeypatch):
    """A client with extracted data and an Aetna template; generation is stubbed."""
    monkeypatch.setattr("data.store.DB_PATH", TEST_DB_PATH)
    import data.store as store
    import pipeline.generator as gen

    store.init_db()
    with open(FIXTURES / "realistic_extraction.json") as f:
        data = ExtractedClinicalData.model_validate(json.load(f))

    ids = {}
    for label in ("a", "b"):
        cid = store.create_client(display_name=f"Client {label}", payor="aetna")
        pid = store.create_auth_period(cid, "2025-01-01", "2025-06-30")
        store.save_extraction(pid, data, "x.pdf", {"is_complete": True, "score": 1.0})
        ids[label] = (cid, pid)
    store.save_template(
        "aetna", "Aetna", [TemplateSection(key="summary", title="Summary"), TemplateSection(key="plan", title="Plan")]
    )

    counter = {"n": 0}

    def fake_generate(d, template, payor_name, payor_key=""):
        counter["n"] += 1
        text = f"generated text #{counter['n']}"
        return gen.assemble_custom_narrative(
            {"sections": [{"key": "summary", "content": text}, {"key": "plan", "content": text}], "overall_confidence": 0.9},
            template,
            payor_key,
        )

    monkeypatch.setattr(gen, "generate_custom_narrative", fake_generate)
    monkeypatch.setattr(gen, "validate_narrative_against_source", lambda n, d: [])
    yield ids
    for suffix in ("", "-wal", "-shm"):
        extra = Path(str(TEST_DB_PATH) + suffix)
        if extra.exists():
            os.remove(extra)


def _open(ids, label):
    at = AppTest.from_file("app.py", default_timeout=60)
    at.session_state["authentication_status"] = True
    at.session_state["name"] = "T"
    at.session_state["selected_client_id"], at.session_state["selected_period_id"] = ids[label]
    at.run()
    return at.switch_page("pages/5_Generate.py").run()


def _generate(at):
    button = [b for b in at.button if b.label.startswith("Generate ")][0]
    return button.click().run()


def _editor_values(at):
    return [t.value for t in at.text_area]


def test_regenerating_replaces_earlier_edits(seeded):
    at = _generate(_open(seeded, "a"))
    assert _editor_values(at) == ["generated text #1", "generated text #1"]

    at.text_area[0].set_value("my hand edit").run()
    assert _editor_values(at)[0] == "my hand edit"

    at = _generate(at)
    assert _editor_values(at) == ["generated text #2", "generated text #2"]


def test_edits_do_not_leak_between_periods(seeded):
    at = _generate(_open(seeded, "a"))
    at.text_area[0].set_value("edit for client a").run()

    # Same browser session, now working on another client's period
    at.session_state["selected_client_id"], at.session_state["selected_period_id"] = seeded["b"]
    at.session_state["narrative"] = None
    at.run()
    at = _generate(at)
    assert "edit for client a" not in _editor_values(at)
