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
