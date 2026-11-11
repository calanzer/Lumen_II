"""Pydantic models for the generated reauthorization narrative sections."""

from pydantic import BaseModel, Field
from typing import Optional


class NarrativeSection(BaseModel):
    """A single section of the reauthorization narrative."""
    section_name: str
    content: str
    source_data_keys: list[str] = Field(
        default_factory=list,
        description="Which ExtractedClinicalData fields were used to generate this section"
    )
    requires_review: bool = Field(
        default=False,
        description="Flagged if data was incomplete or confidence was low"
    )
    review_note: Optional[str] = None


class AnthemReauthNarrative(BaseModel):
    """
    Complete reauthorization narrative structured for Anthem Blue Cross CA.
    Each section maps to Anthem's MCG Care Guidelines structure.
    """
    # Section 1: Client Overview
    client_overview: NarrativeSection = Field(
        description="Demographics, diagnosis, auth period, supervising BCBA"
    )

    # Section 2: Assessment Summary
    assessment_summary: NarrativeSection = Field(
        description="Standardized assessment results with score comparisons to prior period"
    )

    # Section 3: Skill Acquisition Progress
    skill_acquisition_progress: NarrativeSection = Field(
        description="Mastered targets, acquisition rates, generalization data"
    )

    # Section 4: Behavior Reduction Progress
    behavior_reduction_progress: NarrativeSection = Field(
        description="Behavior trends vs baselines, intervention effectiveness, operational definitions"
    )

    # Section 5: Treatment Plan Update
    treatment_plan_update: NarrativeSection = Field(
        description="Goal status, modifications with rationale, new goals if applicable"
    )

    # Section 6: Hours Utilization & Justification
    hours_justification: NarrativeSection = Field(
        description="Hours used vs authorized, explanation for variance, requested hours with justification"
    )

    # Section 7: Caregiver Training
    caregiver_training_summary: NarrativeSection = Field(
        description="Training provided, parent skill acquisition, barriers"
    )

    # Section 8: Medical Necessity Statement
    medical_necessity: NarrativeSection = Field(
        description="Why continued ABA at requested intensity is medically necessary. "
                    "Must reference functional impairment, risk of regression, and ASD core deficits."
    )

    # Section 9: Discharge Plan
    discharge_plan: NarrativeSection = Field(
        description="Measurable discharge criteria, estimated timeline, transition strategy"
    )

    # Metadata
    overall_confidence: float = Field(ge=0, le=1, description="Pipeline confidence score")
    flags_for_bcba: list[str] = Field(default_factory=list, description="Items requiring clinician attention")
    source_hash: Optional[str] = Field(None, description="Fingerprint of the data this was drafted from")


# ── Template-driven narratives ───────────────────────────────────────
# A practice can upload a past approved report for a payor; only its *structure*
# (section titles, what each covers, writing style) is kept as a ReauthTemplate.
# Narratives generated from one are CustomNarrative, with sections in template order.

ANTHEM_SECTIONS: list[tuple[str, str]] = [
    ("client_overview", "Client Overview"),
    ("assessment_summary", "Assessment Summary"),
    ("skill_acquisition_progress", "Skill Acquisition Progress"),
    ("behavior_reduction_progress", "Behavior Reduction Progress"),
    ("treatment_plan_update", "Treatment Plan Update"),
    ("hours_justification", "Hours Utilization & Justification"),
    ("caregiver_training_summary", "Caregiver Training"),
    ("medical_necessity", "Medical Necessity Statement"),
    ("discharge_plan", "Discharge Plan"),
]


class TemplateSection(BaseModel):
    """One section of a payor template: its heading and what it should cover."""
    key: str
    title: str
    guidance: str = ""


class ReauthTemplate(BaseModel):
    """Structure and style of a practice's reauthorization report for one payor."""
    id: Optional[str] = None
    payor: str = ""
    name: str = ""
    sections: list[TemplateSection]
    style_notes: str = ""
    source_filename: Optional[str] = None


class KeyedSection(NarrativeSection):
    """A narrative section tied to a template section."""
    key: str

    def title_or_name(self) -> str:
        return self.section_name or self.key


class CustomNarrative(BaseModel):
    """Narrative whose sections follow a practice-supplied template."""
    payor_key: str = ""
    template_name: str = ""
    sections: list[KeyedSection]
    overall_confidence: float = Field(default=0.0, ge=0, le=1)
    flags_for_bcba: list[str] = Field(default_factory=list)
    source_hash: Optional[str] = None


Narrative = AnthemReauthNarrative | CustomNarrative


def get_sections(narrative: Narrative) -> list[tuple[str, str, NarrativeSection]]:
    """Ordered (key, display title, section) for either narrative type."""
    if isinstance(narrative, CustomNarrative):
        return [(s.key, s.title_or_name(), s) for s in narrative.sections]
    return [(key, title, getattr(narrative, key)) for key, title in ANTHEM_SECTIONS]


def parse_narrative(raw_json: str) -> Narrative:
    """Parse stored narrative JSON into whichever narrative type it holds."""
    import json

    if "sections" in json.loads(raw_json):
        return CustomNarrative.model_validate_json(raw_json)
    return AnthemReauthNarrative.model_validate_json(raw_json)
