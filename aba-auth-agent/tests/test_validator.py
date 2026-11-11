"""Tests for the completeness validator."""

import json
from pathlib import Path

from schemas.clinical_data import ExtractedClinicalData
from pipeline.validator import validate_completeness


def test_complete_data_passes_validation():
    """A fully populated dataset should pass validation."""
    sample_path = Path(__file__).parent.parent / "prompts" / "examples" / "sample_extraction.json"
    with open(sample_path) as f:
        data = json.load(f)
    data["source_filename"] = "test.pdf"
    data["extraction_timestamp"] = "2025-01-01T00:00:00"

    clinical_data = ExtractedClinicalData.model_validate(data)
    result = validate_completeness(clinical_data)

    assert result["is_complete"] is True
    assert result["score"] == 1.0
    assert len(result["missing"]) == 0


def test_empty_data_fails_validation():
    """An empty dataset should fail validation with all fields missing."""
    clinical_data = ExtractedClinicalData(
        source_filename="test.pdf",
        extraction_timestamp="2025-01-01T00:00:00",
    )
    result = validate_completeness(clinical_data)

    assert result["is_complete"] is False
    assert result["score"] < 1.0
    assert len(result["missing"]) > 0


def test_low_utilization_generates_warning():
    """Low utilization without explanation should generate a warning."""
    sample_path = Path(__file__).parent.parent / "prompts" / "examples" / "sample_extraction.json"
    with open(sample_path) as f:
        data = json.load(f)
    data["source_filename"] = "test.pdf"
    data["extraction_timestamp"] = "2025-01-01T00:00:00"
    # Set low utilization without explanation
    data["hours_utilization"][2]["utilization_pct"] = 50.0
    data["hours_utilization"][2]["explanation_if_low"] = None

    clinical_data = ExtractedClinicalData.model_validate(data)
    result = validate_completeness(clinical_data)

    assert any("utilization" in w.lower() for w in result["warnings"])


class TestLowUtilizationFromUnits:
    """Reports often omit the utilization percentage; it must be computed from the units."""

    def _data_with_hours(self, authorized, utilized, pct=None, explanation=None):
        import json
        from pathlib import Path

        from schemas.clinical_data import ExtractedClinicalData

        with open(Path(__file__).parent / "fixtures" / "realistic_extraction.json") as f:
            data = json.load(f)
        data["hours_utilization"] = [
            {
                "cpt_code": "97153",
                "authorized_units": authorized,
                "utilized_units": utilized,
                "utilization_pct": pct,
                "explanation_if_low": explanation,
            }
        ]
        return ExtractedClinicalData.model_validate(data)

    def test_flags_low_utilization_when_percentage_not_stated(self):
        from pipeline.validator import validate_completeness

        result = validate_completeness(self._data_with_hours(1560, 910))
        assert any("97153" in w and "58%" in w for w in result["warnings"])

    def test_explanation_clears_the_warning(self):
        from pipeline.validator import validate_completeness

        result = validate_completeness(self._data_with_hours(1560, 910, explanation="Two illnesses."))
        assert not any("97153" in w for w in result["warnings"])

    def test_healthy_utilization_not_flagged(self):
        from pipeline.validator import validate_completeness

        result = validate_completeness(self._data_with_hours(2080, 1872))
        assert not any("97153" in w for w in result["warnings"])
