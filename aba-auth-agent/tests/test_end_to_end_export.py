"""End-to-end tests: realistic clinical data -> narrative -> DOCX export.

These tests use pre-built fixtures (no API calls) to validate the full
extraction-to-document pipeline with industry-realistic ABA data.
"""

import json
from io import BytesIO
from pathlib import Path

import pytest
from docx import Document

from schemas.clinical_data import ExtractedClinicalData
from schemas.narrative import AnthemReauthNarrative
from pipeline.exporter import export_to_docx, list_available_payors, PAYOR_TEMPLATES
from pipeline.validator import validate_completeness


FIXTURES = Path(__file__).parent / "fixtures"


@pytest.fixture
def realistic_clinical_data() -> ExtractedClinicalData:
    with open(FIXTURES / "realistic_extraction.json") as f:
        data = json.load(f)
    return ExtractedClinicalData.model_validate(data)


@pytest.fixture
def realistic_narrative() -> AnthemReauthNarrative:
    with open(FIXTURES / "realistic_narrative.json") as f:
        data = json.load(f)
    return AnthemReauthNarrative.model_validate(data)


# --- Schema validation with realistic data ---

class TestRealisticSchemaValidation:
    def test_extraction_schema_accepts_realistic_data(self, realistic_clinical_data):
        """Full realistic extraction round-trips through Pydantic."""
        assert realistic_clinical_data.client.client_id == "CR-2024-0847"
        assert realistic_clinical_data.client.age_years == 4
        assert len(realistic_clinical_data.client.diagnosis_codes) == 2
        assert realistic_clinical_data.client.diagnosis_codes[0] == "F84.0"
        assert realistic_clinical_data.client.diagnosis_codes[1] == "F80.2"

    def test_all_assessments_parsed(self, realistic_clinical_data):
        """3 assessments: VB-MAPP, Vineland-3, CARS-2."""
        assert len(realistic_clinical_data.assessments) == 3
        types = [a.assessment_type.value for a in realistic_clinical_data.assessments]
        assert "VB-MAPP" in types
        assert "Vineland-3" in types
        assert "Other" in types  # CARS-2

    def test_vbmapp_domain_scores(self, realistic_clinical_data):
        """VB-MAPP should have 16 domain scores."""
        vbmapp = next(a for a in realistic_clinical_data.assessments if a.assessment_type.value == "VB-MAPP")
        assert len(vbmapp.domain_scores) == 16
        assert vbmapp.domain_scores["Mand"] == 10.5
        assert vbmapp.domain_scores["Intraverbal"] == 2.5

    def test_vineland_score_improvement(self, realistic_clinical_data):
        """Vineland-3 should show improvement from 58 to 62."""
        vineland = next(a for a in realistic_clinical_data.assessments if a.assessment_type.value == "Vineland-3")
        assert vineland.standard_score == 62.0
        assert vineland.previous_score == 58.0
        assert vineland.percentile == 1.0

    def test_skill_acquisition_counts(self, realistic_clinical_data):
        """10 skill targets: 5 mastered, 5 in acquisition."""
        targets = realistic_clinical_data.skill_acquisition_targets
        assert len(targets) == 10
        mastered = sum(1 for t in targets if t.is_mastered)
        assert mastered == 5
        assert len(targets) - mastered == 5

    def test_behavior_operational_definitions_are_detailed(self, realistic_clinical_data):
        """Operational definitions should be ≥50 chars (realistic clinical detail)."""
        for b in realistic_clinical_data.behavior_reduction_targets:
            assert len(b.operational_definition) >= 50, (
                f"Behavior '{b.behavior_name}' has a too-brief operational definition"
            )

    def test_behavior_trends_all_decreasing(self, realistic_clinical_data):
        """All 3 behaviors should show decreasing trends."""
        for b in realistic_clinical_data.behavior_reduction_targets:
            assert b.trend.value == "decreasing"
            assert b.current_value < b.baseline_value

    def test_hours_utilization_cpt_codes(self, realistic_clinical_data):
        """Should have 4 CPT codes including assessment."""
        codes = [h.cpt_code.value for h in realistic_clinical_data.hours_utilization]
        assert "97153" in codes  # direct
        assert "97155" in codes  # supervision
        assert "97156" in codes  # caregiver
        assert "97151" in codes  # assessment

    def test_low_utilization_has_explanation(self, realistic_clinical_data):
        """97156 at 75% should have an explanation."""
        caregiver = next(h for h in realistic_clinical_data.hours_utilization if h.cpt_code.value == "97156")
        assert caregiver.utilization_pct == 75.0
        assert caregiver.explanation_if_low is not None
        assert len(caregiver.explanation_if_low) > 20

    def test_treatment_goal_modification(self, realistic_clinical_data):
        """Goal 4 should be modified with rationale."""
        goal4 = next(g for g in realistic_clinical_data.treatment_goals if g.goal_number == 4)
        assert goal4.status == "modified"
        assert goal4.modification_rationale is not None
        assert "7 routines" in goal4.modification_rationale

    def test_caregiver_training_detail(self, realistic_clinical_data):
        """Caregiver training should have ≥9 topics and barriers documented."""
        ct = realistic_clinical_data.caregiver_training
        assert ct.total_sessions == 14
        assert len(ct.topics_covered) >= 9
        assert ct.barriers_to_participation is not None
        assert "Spanish" in ct.barriers_to_participation  # bilingual component

    def test_discharge_plan_has_6_criteria(self, realistic_clinical_data):
        """Discharge plan should have 6 measurable criteria."""
        dp = realistic_clinical_data.discharge_plan
        assert len(dp.measurable_criteria) == 6

    def test_narrative_schema_accepts_realistic_data(self, realistic_narrative):
        """Realistic narrative round-trips through Pydantic."""
        assert realistic_narrative.overall_confidence == 0.95
        assert len(realistic_narrative.flags_for_bcba) == 4


# --- Validator tests with realistic data ---

class TestRealisticValidation:
    def test_realistic_data_is_complete(self, realistic_clinical_data):
        """Realistic fully-populated data should pass validation."""
        result = validate_completeness(realistic_clinical_data)
        assert result["is_complete"] is True
        assert result["score"] == 1.0
        assert len(result["missing"]) == 0

    def test_low_utilization_warning(self, realistic_clinical_data):
        """97156 at 75% but with explanation should NOT trigger the no-explanation warning."""
        result = validate_completeness(realistic_clinical_data)
        utilization_warnings = [w for w in result["warnings"] if "utilization" in w.lower()]
        # Should not warn because explanation_if_low is provided
        assert len(utilization_warnings) == 0

    def test_warns_on_vague_operational_definition(self):
        """Short operational definitions should trigger a warning."""
        data = ExtractedClinicalData(
            source_filename="test.pdf",
            extraction_timestamp="2025-01-01T00:00:00",
            client={"diagnosis_codes": ["F84.0"], "auth_period_start": "2025-01-01",
                     "auth_period_end": "2025-06-30", "supervising_bcba": "Test BCBA"},
            assessments=[{"assessment_type": "VB-MAPP", "assessment_name": "VB-MAPP",
                         "date_administered": "2025-06-01"}],
            skill_acquisition_targets=[{"domain": "Test", "target_name": "Test target"}],
            behavior_reduction_targets=[{
                "behavior_name": "Hitting",
                "operational_definition": "Hits others",  # too vague
                "measurement_type": "frequency",
                "baseline_value": 5.0
            }],
            hours_utilization=[{"cpt_code": "97153", "authorized_units": 100, "utilized_units": 90}],
            treatment_goals=[{"goal_number": 1, "goal_area": "Test", "goal_statement": "Test goal",
                            "target_criterion": "80%", "status": "in progress"}],
            caregiver_training={"total_sessions": 5},
            discharge_plan={"measurable_criteria": ["Criterion 1"]},
        )
        result = validate_completeness(data)
        vague_warnings = [w for w in result["warnings"] if "vague" in w.lower()]
        assert len(vague_warnings) == 1


# --- DOCX export tests ---

class TestDocxExport:
    def test_anthem_export_produces_valid_docx(self, realistic_clinical_data, realistic_narrative):
        """Export to Anthem template produces a readable Word document."""
        docx_bytes = export_to_docx(realistic_clinical_data, realistic_narrative, payor_key="anthem_blue_cross_ca")
        assert len(docx_bytes) > 1000  # Non-trivial file

        # Verify it's a valid DOCX
        doc = Document(BytesIO(docx_bytes))
        full_text = "\n".join(p.text for p in doc.paragraphs)

        # Check key content is present
        assert "CR-2024-0847" in full_text
        assert "F84.0" in full_text
        assert "Dr. Maria Gonzalez" in full_text
        assert "2025-07-01" in full_text

    def test_all_narrative_sections_in_docx(self, realistic_clinical_data, realistic_narrative):
        """All 9 narrative sections should appear in the DOCX."""
        docx_bytes = export_to_docx(realistic_clinical_data, realistic_narrative)
        doc = Document(BytesIO(docx_bytes))
        full_text = "\n".join(p.text for p in doc.paragraphs)

        # Check each section's content appears
        assert "4-year-old male" in full_text
        assert "VB-MAPP" in full_text
        assert "5 of 10 active skill acquisition targets" in full_text
        assert "8.3 episodes per hour" in full_text
        assert "Goal 1 (Communication)" in full_text
        assert "580 of 624 authorized units" in full_text
        assert "14 caregiver training sessions" in full_text
        assert "medically necessary" in full_text.lower()
        assert "0 of 6 discharge criteria" in full_text

    def test_docx_has_ai_disclosure(self, realistic_clinical_data, realistic_narrative):
        """DOCX must contain AI disclosure statement."""
        docx_bytes = export_to_docx(realistic_clinical_data, realistic_narrative)
        doc = Document(BytesIO(docx_bytes))
        full_text = "\n".join(p.text for p in doc.paragraphs)
        assert "AI assistance" in full_text

    def test_all_payor_templates_generate(self, realistic_clinical_data, realistic_narrative):
        """Every registered payor should produce a valid DOCX."""
        for payor_key in PAYOR_TEMPLATES:
            docx_bytes = export_to_docx(realistic_clinical_data, realistic_narrative, payor_key=payor_key)
            assert len(docx_bytes) > 1000, f"{payor_key} produced empty/tiny DOCX"
            doc = Document(BytesIO(docx_bytes))
            assert len(doc.paragraphs) > 10, f"{payor_key} has too few paragraphs"

    def test_payor_list_returns_all_entries(self):
        """list_available_payors should return all 5 payors."""
        payors = list_available_payors()
        assert len(payors) == 5
        assert "anthem_blue_cross_ca" in payors
        assert "aetna" in payors
        assert "medi_cal" in payors

    def test_export_with_missing_client_id_uses_placeholder(self, realistic_narrative):
        """When client_id is None, DOCX should use [CLIENT ID] placeholder."""
        data = ExtractedClinicalData(
            source_filename="test.pdf",
            extraction_timestamp="2025-01-01T00:00:00",
        )
        docx_bytes = export_to_docx(data, realistic_narrative)
        doc = Document(BytesIO(docx_bytes))
        full_text = "\n".join(p.text for p in doc.paragraphs)
        assert "[CLIENT ID]" in full_text


# --- Narrative content quality checks ---

class TestNarrativeQuality:
    def test_medical_necessity_addresses_all_requirements(self, realistic_narrative):
        """Medical necessity must address: impairment, regression risk, ASD deficits, intensity rationale."""
        content = realistic_narrative.medical_necessity.content.lower()
        assert "functional impairment" in content or "impairment" in content
        assert "regression" in content
        assert "asd" in content or "autism" in content
        assert "intensity" in content or "requested" in content

    def test_behavior_section_includes_baselines_and_currents(self, realistic_narrative):
        """Behavior section should state baseline and current values."""
        content = realistic_narrative.behavior_reduction_progress.content
        assert "8.3" in content  # aggression baseline
        assert "2.7" in content  # aggression current
        assert "45" in content   # stereotypy baseline (percent)
        assert "32" in content   # stereotypy current
        assert "3.1" in content  # elopement baseline
        assert "0.8" in content  # elopement current

    def test_hours_section_includes_all_cpt_codes(self, realistic_narrative):
        """Hours section should reference all 4 CPT codes."""
        content = realistic_narrative.hours_justification.content
        assert "97153" in content
        assert "97155" in content
        assert "97156" in content
        assert "97151" in content

    def test_discharge_plan_has_quantitative_criteria(self, realistic_narrative):
        """Discharge plan should have specific numeric benchmarks."""
        content = realistic_narrative.discharge_plan.content
        assert "1.0 episodes per hour" in content  # aggression criterion
        assert "0.3 episodes per hour" in content  # elopement criterion
        assert "20%" in content                     # stereotypy criterion
        assert "90%" in content                     # fidelity criterion
        assert "70" in content                      # Vineland criterion

    def test_no_section_requires_review(self, realistic_narrative):
        """With complete data, no section should require review."""
        sections = [
            realistic_narrative.client_overview,
            realistic_narrative.assessment_summary,
            realistic_narrative.skill_acquisition_progress,
            realistic_narrative.behavior_reduction_progress,
            realistic_narrative.treatment_plan_update,
            realistic_narrative.hours_justification,
            realistic_narrative.caregiver_training_summary,
            realistic_narrative.medical_necessity,
            realistic_narrative.discharge_plan,
        ]
        for section in sections:
            assert section.requires_review is False, (
                f"Section '{section.section_name}' should not require review with complete data"
            )

    def test_narrative_sections_meet_word_count(self, realistic_narrative):
        """Each section should be 100-400 words (clinical standard)."""
        sections = [
            realistic_narrative.client_overview,
            realistic_narrative.assessment_summary,
            realistic_narrative.skill_acquisition_progress,
            realistic_narrative.behavior_reduction_progress,
            realistic_narrative.treatment_plan_update,
            realistic_narrative.hours_justification,
            realistic_narrative.caregiver_training_summary,
            realistic_narrative.medical_necessity,
            realistic_narrative.discharge_plan,
        ]
        for section in sections:
            word_count = len(section.content.split())
            assert word_count >= 50, (
                f"Section '{section.section_name}' is too short ({word_count} words)"
            )
            assert word_count <= 500, (
                f"Section '{section.section_name}' is too long ({word_count} words)"
            )
