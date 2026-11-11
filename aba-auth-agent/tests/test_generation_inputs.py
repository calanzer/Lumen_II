"""What the drafting and checking models are actually sent."""

import json
from pathlib import Path
from types import SimpleNamespace

import pytest

import pipeline.generator as gen
from schemas.clinical_data import ExtractedClinicalData
from schemas.narrative import ReauthTemplate, TemplateSection

FIXTURES = Path(__file__).parent / "fixtures"


@pytest.fixture
def data():
    with open(FIXTURES / "realistic_extraction.json") as f:
        return ExtractedClinicalData.model_validate(json.load(f))


@pytest.fixture
def captured(monkeypatch):
    """Capture the request instead of calling the API; reply with the realistic narrative."""
    sent = {}
    with open(FIXTURES / "realistic_narrative.json") as f:
        reply = f.read()

    class FakeMessages:
        def create(self, **kwargs):
            sent.update(kwargs)
            return SimpleNamespace(stop_reason="end_turn", content=[SimpleNamespace(type="text", text=reply)])

    monkeypatch.setattr(gen.anthropic, "Anthropic", lambda: SimpleNamespace(messages=FakeMessages()))
    return sent


def _system_text(sent):
    system = sent["system"]
    return system if isinstance(system, str) else system[0]["text"]


def test_clinical_json_leaves_out_the_apps_bookkeeping(data):
    text = gen.clinical_json(data)
    for field in ("extraction_timestamp", "extraction_model", "source_filename"):
        assert field not in text
    assert "VB-MAPP" in text  # real clinical content is still there


def test_default_layout_names_the_clients_payor_not_anthem(captured, data):
    gen.generate_narrative(data, "Aetna")

    assert "Aetna" in _system_text(captured)
    assert "Anthem" not in _system_text(captured)
    user = captured["messages"][0]["content"]
    assert "Generate the complete Aetna reauthorization narrative" in user
    assert "Anthem" not in user


def test_default_payor_is_still_anthem(captured, data):
    gen.generate_narrative(data)
    assert "Anthem Blue Cross California" in _system_text(captured)


def test_the_model_is_shown_the_data_not_a_function(captured, data):
    gen.generate_narrative(data, "Aetna")
    user = captured["messages"][0]["content"]
    assert "<function" not in user and "<clinical_data>" in user
    assert "extraction_timestamp" not in user
    assert data.client.client_id in user


def test_custom_generation_also_hides_bookkeeping(monkeypatch, data):
    sent = {}

    class FakeMessages:
        def create(self, **kwargs):
            sent.update(kwargs)
            return SimpleNamespace(
                stop_reason="end_turn",
                content=[SimpleNamespace(type="text", text=json.dumps({"sections": [{"key": "a", "content": "x"}]}))],
            )

    monkeypatch.setattr(gen.anthropic, "Anthropic", lambda: SimpleNamespace(messages=FakeMessages()))
    template = ReauthTemplate(sections=[TemplateSection(key="a", title="A")])
    gen.generate_custom_narrative(data, template, "Aetna", "aetna")

    user = sent["messages"][0]["content"]
    assert "extraction_timestamp" not in user and "<clinical_data>" in user


def test_cross_check_sees_the_same_cleaned_data(monkeypatch, data):
    sent = {}

    class FakeMessages:
        def create(self, **kwargs):
            sent.update(kwargs)
            return SimpleNamespace(stop_reason="end_turn", content=[SimpleNamespace(type="text", text="[]")])

    monkeypatch.setattr(gen.anthropic, "Anthropic", lambda: SimpleNamespace(messages=FakeMessages()))
    with open(FIXTURES / "realistic_narrative.json") as f:
        from schemas.narrative import AnthemReauthNarrative

        narrative = AnthemReauthNarrative.model_validate(json.load(f))
    assert gen.extract_narrative_claims(narrative, data) == []
    assert "extraction_timestamp" not in sent["messages"][0]["content"]


def test_cross_check_has_room_for_a_long_claim_list(monkeypatch, data):
    """A 150-claim narrative was cut off at 8,000 tokens and the check silently failed."""
    sent = {}

    class FakeMessages:
        def create(self, **kwargs):
            sent.update(kwargs)
            return SimpleNamespace(stop_reason="end_turn", content=[SimpleNamespace(type="text", text="[]")])

    monkeypatch.setattr(gen.anthropic, "Anthropic", lambda: SimpleNamespace(messages=FakeMessages()))
    with open(FIXTURES / "realistic_narrative.json") as f:
        from schemas.narrative import AnthemReauthNarrative

        narrative = AnthemReauthNarrative.model_validate(json.load(f))
    gen.extract_narrative_claims(narrative, data)
    assert sent["max_tokens"] >= 16000
