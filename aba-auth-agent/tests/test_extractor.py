"""Tests for the extraction pipeline."""

import json
from pathlib import Path

from schemas.clinical_data import ExtractedClinicalData


def test_schema_loads_sample_extraction():
    """Verify the sample extraction JSON validates against the Pydantic schema."""
    sample_path = Path(__file__).parent.parent / "prompts" / "examples" / "sample_extraction.json"
    with open(sample_path) as f:
        data = json.load(f)

    # Add required metadata fields
    data["source_filename"] = "test.pdf"
    data["extraction_timestamp"] = "2025-01-01T00:00:00"

    result = ExtractedClinicalData.model_validate(data)
    assert result.source_filename == "test.pdf"
    assert len(result.assessments) == 1
    assert result.assessments[0].assessment_type.value == "VB-MAPP"
    assert len(result.skill_acquisition_targets) == 2
    assert len(result.behavior_reduction_targets) == 1
    assert len(result.hours_utilization) == 3
    assert len(result.treatment_goals) == 1
    assert result.caregiver_training.total_sessions == 8
    assert len(result.discharge_plan.measurable_criteria) == 4


def test_schema_handles_minimal_data():
    """Verify the schema accepts minimal data with defaults."""
    data = {
        "source_filename": "test.pdf",
        "extraction_timestamp": "2025-01-01T00:00:00",
    }
    result = ExtractedClinicalData.model_validate(data)
    assert result.client.diagnosis_codes == []
    assert result.assessments == []
    assert result.skill_acquisition_targets == []
    assert result.missing_fields == []
