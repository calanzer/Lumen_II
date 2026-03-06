"""Pydantic models for structured clinical data extraction from ABA progress reports."""

from __future__ import annotations
from datetime import date
from enum import Enum
from typing import Optional
from pydantic import BaseModel, Field


class AssessmentType(str, Enum):
    VB_MAPP = "VB-MAPP"
    ABLLS_R = "ABLLS-R"
    VINELAND_3 = "Vineland-3"
    PEAK = "PEAK"
    AFLS = "AFLS"
    OTHER = "Other"


class CPTCode(str, Enum):
    """ABA-specific CPT and HCPCS codes."""
    ASSESSMENT_97151 = "97151"
    ADAPTIVE_BEHAVIOR_97153 = "97153"
    GROUP_ADAPTIVE_97154 = "97154"
    PROTOCOL_MOD_97155 = "97155"
    CAREGIVER_TRAINING_97156 = "97156"
    CAREGIVER_GROUP_97157 = "97157"
    LEAD_TECH_0362T = "0362T"
    TECH_GROUP_0373T = "0373T"
    # Medi-Cal HCPCS alternatives
    ASSESSMENT_H0031 = "H0031"
    PLAN_DEV_H0032 = "H0032"
    BHT_DIRECT_H2019 = "H2019"
    SUPERVISION_H2012 = "H2012"
    FAMILY_TRAINING_S5111 = "S5111"


class BehaviorTrend(str, Enum):
    INCREASING = "increasing"
    DECREASING = "decreasing"
    STABLE = "stable"
    VARIABLE = "variable"


class SkillAcquisitionTarget(BaseModel):
    """Individual skill acquisition target with mastery data."""
    domain: str = Field(description="Skill domain (e.g., 'Manding', 'Tacting', 'Social Skills', 'Daily Living')")
    target_name: str = Field(description="Specific target (e.g., 'Mands for 20 different items independently')")
    date_introduced: Optional[date] = None
    date_mastered: Optional[date] = None
    is_mastered: bool = False
    current_accuracy_pct: Optional[float] = Field(None, ge=0, le=100)
    mastery_criterion_pct: float = Field(default=80.0, ge=0, le=100)
    generalization_demonstrated: bool = False
    notes: Optional[str] = None


class BehaviorReductionTarget(BaseModel):
    """Individual behavior reduction target with trend data."""
    behavior_name: str = Field(description="Operational definition (e.g., 'Elopement: leaving designated area without permission')")
    operational_definition: str = Field(description="Full operational definition with measurable terms")
    measurement_type: str = Field(description="frequency, duration, rate, interval, latency")
    baseline_value: Optional[float] = None
    baseline_date: Optional[date] = None
    current_value: Optional[float] = None
    current_date: Optional[date] = None
    trend: Optional[BehaviorTrend] = None
    unit: str = Field(default="per hour", description="e.g., 'per hour', 'minutes per episode', 'percent of intervals'")
    function_of_behavior: Optional[str] = Field(None, description="e.g., 'escape from demands', 'access to tangibles'")
    intervention_strategies: list[str] = Field(default_factory=list)


class StandardizedAssessment(BaseModel):
    """Standardized assessment scores."""
    assessment_type: AssessmentType
    assessment_name: str = Field(description="Full name if Other type")
    date_administered: Optional[date] = None
    raw_score: Optional[float] = None
    standard_score: Optional[float] = None
    percentile: Optional[float] = None
    age_equivalent: Optional[str] = None
    domain_scores: dict[str, float] = Field(default_factory=dict, description="Sub-domain scores keyed by domain name")
    previous_score: Optional[float] = Field(None, description="Score from prior auth period for comparison")
    previous_date: Optional[date] = None


class HoursUtilization(BaseModel):
    """Authorized vs utilized hours by CPT code."""
    cpt_code: CPTCode
    authorized_units: float = Field(description="Units authorized for the auth period")
    utilized_units: float = Field(description="Units actually delivered")
    utilization_pct: Optional[float] = Field(None, ge=0)
    explanation_if_low: Optional[str] = Field(None, description="Required if utilization < 80%")


class TreatmentGoal(BaseModel):
    """Treatment plan goal with measurable criteria."""
    goal_number: int
    goal_area: str = Field(description="e.g., 'Communication', 'Social Skills', 'Adaptive Behavior', 'Behavior Reduction'")
    goal_statement: str = Field(description="Full measurable goal statement")
    baseline_performance: Optional[str] = None
    current_performance: Optional[str] = None
    target_criterion: str = Field(description="e.g., '80% accuracy across 3 consecutive sessions'")
    status: str = Field(description="'in progress', 'met', 'modified', 'discontinued'")
    modification_rationale: Optional[str] = Field(None, description="Required if status is 'modified' or 'discontinued'")
    related_targets: list[str] = Field(default_factory=list)


class CaregiverTraining(BaseModel):
    """Caregiver/parent training documentation."""
    total_sessions: int = Field(default=0)
    topics_covered: list[str] = Field(default_factory=list)
    caregiver_skill_acquisition: Optional[str] = Field(None, description="Description of parent skill generalization")
    barriers_to_participation: Optional[str] = None


class ClientDemographics(BaseModel):
    """Client identifying information (PHI — handle with HIPAA compliance)."""
    client_id: Optional[str] = Field(None, description="Internal ID only, no SSN/DOB in extraction")
    age_years: Optional[int] = None
    diagnosis_codes: list[str] = Field(default_factory=list, description="ICD-10 codes, e.g., ['F84.0']")
    diagnosis_descriptions: list[str] = Field(default_factory=list)
    auth_period_start: Optional[date] = None
    auth_period_end: Optional[date] = None
    supervising_bcba: Optional[str] = None
    bcba_credential_number: Optional[str] = None


class DischargePlan(BaseModel):
    """Discharge criteria and transition planning."""
    measurable_criteria: list[str] = Field(default_factory=list, description="Specific criteria that would trigger discharge")
    estimated_discharge_date: Optional[date] = None
    transition_plan: Optional[str] = Field(None, description="Plan for transitioning to lower level of care")
    current_discharge_readiness: Optional[str] = Field(None, description="Assessment of how close client is to discharge criteria")


class ExtractedClinicalData(BaseModel):
    """
    Top-level schema for all clinical data extracted from an ABA progress report.
    This is the SINGLE SOURCE OF TRUTH that feeds into narrative generation.
    """
    # Metadata
    source_filename: str
    extraction_timestamp: str
    extraction_model: str = "claude-sonnet-4-20250514"
    confidence_notes: list[str] = Field(default_factory=list, description="Any extraction uncertainties")

    # Clinical data
    client: ClientDemographics = Field(default_factory=ClientDemographics)
    assessments: list[StandardizedAssessment] = Field(default_factory=list)
    skill_acquisition_targets: list[SkillAcquisitionTarget] = Field(default_factory=list)
    behavior_reduction_targets: list[BehaviorReductionTarget] = Field(default_factory=list)
    hours_utilization: list[HoursUtilization] = Field(default_factory=list)
    treatment_goals: list[TreatmentGoal] = Field(default_factory=list)
    caregiver_training: CaregiverTraining = Field(default_factory=CaregiverTraining)
    discharge_plan: DischargePlan = Field(default_factory=DischargePlan)

    # Recommended hours for next auth period
    requested_hours_by_code: dict[str, float] = Field(default_factory=dict, description="CPT code -> weekly units requested")
    clinical_justification_for_hours: Optional[str] = None

    # Completeness tracking
    missing_fields: list[str] = Field(default_factory=list, description="Fields the validator could not populate")
