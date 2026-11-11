"""Tests for tracing narrative numbers back to the extracted source data."""

import pytest

from pipeline.claim_check import find_discrepancies, numbers_in

SOURCE = {
    "client": {"client_id": "HB-1", "diagnosis_codes": ["F84.0", "F80.9"], "auth_period_start": "2026-01-01"},
    "assessments": [
        {"assessment_name": "VB-MAPP", "raw_score": 98.5, "previous_score": 84.0, "date_administered": "2026-06-10"},
        {"assessment_name": "Vineland-3", "standard_score": 72, "previous_score": 66},
    ],
    "behavior_reduction_targets": [
        {"behavior_name": "Aggression", "baseline_value": 3.4, "current_value": 0.6, "unit": "per hour"},
        {"behavior_name": "Task refusal", "baseline_value": 7.8, "current_value": 2.2, "unit": "per hour"},
    ],
    "skill_acquisition_targets": [
        {"target_name": "Mands", "is_mastered": True, "current_accuracy_pct": 92},
        {"target_name": "Tacts", "is_mastered": True, "current_accuracy_pct": 88},
        {"target_name": "Play", "is_mastered": False, "current_accuracy_pct": 60},
    ],
    "hours_utilization": [
        {"cpt_code": "97153", "authorized_units": 2080, "utilized_units": 1872},
        {"cpt_code": "97155", "authorized_units": 156, "utilized_units": 148},
    ],
    "requested_hours_by_code": {"97153": 16, "97155": 1.5, "97156": 1.0},
    "discharge_plan": {"measurable_criteria": ["Aggression below 0.5 per hour for 12 consecutive weeks"]},
}


def claim(value, description="claim", section="S"):
    return {"claim": description, "value": value, "section": section}


def flagged(value, description):
    return bool(find_discrepancies([claim(value, description)], SOURCE))


class TestNumbersIn:
    def test_ignores_thousands_separators_and_units(self):
        assert numbers_in("1,872 of 2,080 units (90%)") == [1872.0, 2080.0, 90.0]

    def test_dates_yield_their_parts(self):
        assert numbers_in("06/10/2026") == [6.0, 10.0, 2026.0]


class TestGenuineClaimsAreNotFlagged:
    @pytest.mark.parametrize(
        "value, description",
        [
            ("7.8 per hour", "Task refusal baseline rate"),  # unit text around a source number
            ("1,872 of 2,080", "Utilization CPT 97153 units"),  # separators and wording
            ("06/10/2026", "VB-MAPP administration date"),  # different date format
            ("01/01/2026", "Report period start date"),
            ("F80.9", "ICD-10 code for Language Disorder"),  # identifier appears as written
            ("Below 0.5 per hour for 12 consecutive weeks", "Aggression discharge criterion"),  # inside a list string
            ("80%", "Utilization threshold"),  # a payor rule, not client data
            ("F84.0 Autism Spectrum Disorder, Level 2", "Primary diagnosis code"),  # code inside longer text
            ("97153, 97155", "CPT codes billed"),  # list of billing codes
        ],
    )
    def test_formatting_differences(self, value, description):
        assert not flagged(value, description)

    @pytest.mark.parametrize(
        "value, description",
        [
            ("+14.5", "VB-MAPP total score change"),  # 98.5 - 84.0
            ("14.5 points", "VB-MAPP total gain"),
            ("82%", "Aggression reduction"),  # (3.4 - 0.6) / 3.4
            ("72%", "Task refusal reduction"),  # (7.8 - 2.2) / 7.8
            ("3 of 3", "Number of skill targets"),  # list length
            ("2 of 3 (67%)", "Skill acquisition targets mastered"),  # count of True / length
            ("18.5 hours per week", "Total requested hours"),  # sum of sibling values
        ],
    )
    def test_simple_derived_values(self, value, description):
        assert not flagged(value, description)


class TestFabricatedClaimsAreFlagged:
    @pytest.mark.parametrize(
        "value, description",
        [
            ("9.7 per hour", "Task refusal baseline rate"),
            ("4,310 of 2,080", "Utilization CPT 97153 units"),
            ("131.9", "VB-MAPP total score (current)"),
            ("99%", "Aggression reduction"),
        ],
    )
    def test_invented_numbers(self, value, description):
        assert flagged(value, description)

    def test_a_code_not_in_the_source_is_flagged(self):
        assert flagged("F90.2 ADHD", "Secondary diagnosis code")
        assert flagged("97530", "CPT codes billed")

    def test_a_number_from_the_wrong_record_is_flagged(self):
        # 3.4 is a real number in the source, but it is Aggression's baseline, not Task refusal's
        assert flagged("3.4 per hour", "Task refusal baseline rate")
        assert not flagged("3.4 per hour", "Aggression baseline rate")

    def test_message_names_the_untraced_number(self):
        (message,) = find_discrepancies([claim("9.7 per hour", "Task refusal baseline rate", "Behavior")], SOURCE)
        assert "Behavior" in message and "9.7" in message and "Verify manually" in message


def test_claims_without_numbers_are_ignored():
    assert find_discrepancies([claim("Autism spectrum disorder", "Diagnosis")], {}) == []


def test_accepts_a_pydantic_model_source():
    import json
    from pathlib import Path

    from schemas.clinical_data import ExtractedClinicalData

    with open(Path(__file__).parent / "fixtures" / "realistic_extraction.json") as f:
        data = ExtractedClinicalData.model_validate(json.load(f))
    assert find_discrepancies([claim("F84.0", "Diagnosis code")], data) == []
    assert find_discrepancies([claim("123456.789", "Made up score")], data)
