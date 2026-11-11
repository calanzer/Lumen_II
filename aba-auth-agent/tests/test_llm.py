"""Tests for shared model settings and response handling."""

from types import SimpleNamespace

import pytest

from pipeline import llm


def _message(blocks, stop_reason="end_turn"):
    return SimpleNamespace(stop_reason=stop_reason, content=blocks)


def _text(value):
    return SimpleNamespace(type="text", text=value)


def _thinking():
    return SimpleNamespace(type="thinking", thinking="")


class TestResponseText:
    def test_skips_leading_thinking_block(self):
        assert llm.response_text(_message([_thinking(), _text('{"a": 1}')])) == '{"a": 1}'

    def test_joins_multiple_text_blocks(self):
        assert llm.response_text(_message([_text("one "), _text("two")])) == "one two"

    def test_refusal_raises_readable_error(self):
        with pytest.raises(llm.LLMError, match="declined"):
            llm.response_text(_message([_text("x")], stop_reason="refusal"))

    def test_truncation_raises_instead_of_returning_partial_json(self):
        with pytest.raises(llm.LLMError, match="cut off"):
            llm.response_text(_message([_text('{"half":')], stop_reason="max_tokens"))

    def test_no_text_raises(self):
        with pytest.raises(llm.LLMError, match="empty"):
            llm.response_text(_message([_thinking()]))


def test_models_are_current_ids_without_date_suffixes():
    assert llm.MAIN_MODEL == "claude-sonnet-5-5"
    assert llm.CHECK_MODEL == "claude-haiku-5-5"


def test_no_pipeline_module_hardcodes_a_model_or_sampling_param():
    """Retired model IDs and temperature (rejected by these models) must not creep back."""
    from pathlib import Path

    root = Path(__file__).parent.parent / "pipeline"
    for path in root.glob("*.py"):
        if path.name == "llm.py":
            continue
        source = path.read_text()
        assert "claude-" not in source, f"{path.name} hardcodes a model id"
        assert "temperature" not in source, f"{path.name} sets temperature"
