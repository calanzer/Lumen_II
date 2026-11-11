"""Tests for the extraction pipeline."""

import json
from pathlib import Path

import pytest

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


def test_pdf_table_extraction_reads_tables_from_bytes(tmp_path):
    """Regression: pdfplumber needs a file object, so raw bytes used to raise and the
    table cross-check was silently skipped for every PDF."""
    import sys

    sys.path.insert(0, str(Path(__file__).parent.parent / "samples"))
    import render

    from pipeline.extractor import _extract_tables_with_pdfplumber

    pdf_path = tmp_path / "t.pdf"
    render.to_pdf(
        [("h", "Skills"), ("table", ["Target", "Status", "Accuracy"], [["Mands", "Mastered", "85%"], ["Matching", "In progress", "72%"]])],
        pdf_path,
    )
    tables = _extract_tables_with_pdfplumber(pdf_path.read_bytes())

    assert tables, "expected at least one table"
    flat = [cell for table in tables for row in table for cell in row]
    assert "Mands" in flat and "72%" in flat


class TestNullRepair:
    """Reports often lack whole sections; the model answers null and extraction must not crash."""

    def _base(self):
        from pathlib import Path
        import json

        with open(Path(__file__).parent / "fixtures" / "realistic_extraction.json") as f:
            return json.load(f)

    def test_nulls_in_required_fields_become_flagged_placeholders(self):
        from pipeline.extractor import NOT_STATED_TEXT, _validate_with_null_repair

        data = self._base()
        data["skill_acquisition_targets"][0]["domain"] = None
        data["treatment_goals"][0]["target_criterion"] = None
        data["caregiver_training"]["total_sessions"] = None

        result = _validate_with_null_repair(data)

        assert result.skill_acquisition_targets[0].domain == NOT_STATED_TEXT
        assert result.treatment_goals[0].target_criterion == NOT_STATED_TEXT
        assert result.caregiver_training.total_sessions == 0
        assert "skill_acquisition_targets.0.domain (not stated in report)" in result.missing_fields
        assert "caregiver_training.total_sessions (not stated in report)" in result.missing_fields

    def test_complete_data_is_untouched(self):
        from pipeline.extractor import _validate_with_null_repair

        data = self._base()
        before = list(data.get("missing_fields") or [])
        assert _validate_with_null_repair(data).missing_fields == before

    def test_other_validation_errors_still_raise(self):
        from pydantic import ValidationError

        from pipeline.extractor import _validate_with_null_repair

        data = self._base()
        data["skill_acquisition_targets"][0]["current_accuracy_pct"] = 250  # out of range
        with pytest.raises(ValidationError):
            _validate_with_null_repair(data)
