"""Tests for the narrative generator (schema validation only — API tests require ANTHROPIC_API_KEY)."""

import json
from pathlib import Path

from schemas.narrative import AnthemReauthNarrative


def test_schema_loads_sample_narrative():
    """Verify the sample narrative JSON validates against the Pydantic schema."""
    sample_path = Path(__file__).parent.parent / "prompts" / "examples" / "sample_narrative.json"
    with open(sample_path) as f:
        data = json.load(f)

    result = AnthemReauthNarrative.model_validate(data)
    assert result.overall_confidence == 0.92
    assert len(result.flags_for_bcba) == 2
    assert "Client Overview" in result.client_overview.section_name
    assert result.medical_necessity.requires_review is False


def test_narrative_section_fields():
    """Verify narrative sections have expected structure."""
    sample_path = Path(__file__).parent.parent / "prompts" / "examples" / "sample_narrative.json"
    with open(sample_path) as f:
        data = json.load(f)

    result = AnthemReauthNarrative.model_validate(data)

    sections = [
        result.client_overview,
        result.assessment_summary,
        result.skill_acquisition_progress,
        result.behavior_reduction_progress,
        result.treatment_plan_update,
        result.hours_justification,
        result.caregiver_training_summary,
        result.medical_necessity,
        result.discharge_plan,
    ]

    for section in sections:
        assert section.section_name
        assert len(section.content) > 50
        assert isinstance(section.source_data_keys, list)
        assert isinstance(section.requires_review, bool)
