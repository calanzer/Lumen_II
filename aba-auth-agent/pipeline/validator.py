"""Validate extracted clinical data for completeness against payor requirements."""

from datetime import date, timedelta
from typing import Optional

from schemas.clinical_data import ExtractedClinicalData


# Anthem Blue Cross CA required fields for reauthorization
ANTHEM_REQUIRED_FIELDS = {
    "client.diagnosis_codes": "At least one ICD-10 diagnosis code",
    "client.auth_period_start": "Authorization period start date",
    "client.auth_period_end": "Authorization period end date",
    "client.supervising_bcba": "Supervising BCBA name",
    "assessments": "At least one standardized assessment (VB-MAPP, ABLLS-R, or Vineland-3)",
    "skill_acquisition_targets": "At least one skill acquisition target with mastery data",
    "behavior_reduction_targets": "At least one behavior reduction target with operational definition",
    "hours_utilization": "Hours utilized vs authorized by CPT code",
    "treatment_goals": "At least one treatment goal with measurable criterion",
    "caregiver_training.total_sessions": "Number of caregiver training sessions",
    "discharge_plan.measurable_criteria": "At least one measurable discharge criterion",
}


def _check_assessment_recency(
    assessment_date: Optional[date],
    assessment_name: str,
    max_age_months: int = 12,
) -> Optional[str]:
    """Check if an assessment is within the required recency window."""
    if not assessment_date:
        return None
    cutoff = date.today() - timedelta(days=max_age_months * 30)
    if assessment_date < cutoff:
        age_months = (date.today() - assessment_date).days // 30
        return (
            f"Assessment '{assessment_name}' was administered {age_months} months ago "
            f"(on {assessment_date}). Payors require assessments within {max_age_months} months — "
            f"high denial risk."
        )
    return None


def validate_completeness(data: ExtractedClinicalData) -> dict:
    """
    Check extracted data against Anthem Blue Cross CA requirements.

    Returns:
        {
            "is_complete": bool,
            "missing": [{"field": str, "description": str, "severity": "required"|"recommended"}],
            "warnings": [str],
            "score": float  # 0-1 completeness score
        }
    """
    missing = []
    warnings = []

    # Check each required field
    if not data.client.diagnosis_codes:
        missing.append({"field": "diagnosis_codes", "description": ANTHEM_REQUIRED_FIELDS["client.diagnosis_codes"], "severity": "required"})

    if not data.client.auth_period_start:
        missing.append({"field": "auth_period_start", "description": ANTHEM_REQUIRED_FIELDS["client.auth_period_start"], "severity": "required"})

    if not data.client.auth_period_end:
        missing.append({"field": "auth_period_end", "description": ANTHEM_REQUIRED_FIELDS["client.auth_period_end"], "severity": "required"})

    if not data.client.supervising_bcba:
        missing.append({"field": "supervising_bcba", "description": ANTHEM_REQUIRED_FIELDS["client.supervising_bcba"], "severity": "required"})

    if not data.assessments:
        missing.append({"field": "assessments", "description": ANTHEM_REQUIRED_FIELDS["assessments"], "severity": "required"})
    else:
        for a in data.assessments:
            if not a.date_administered:
                warnings.append(f"Assessment '{a.assessment_name}' is missing administration date — payors require this.")
            else:
                # Check assessment recency — must be within 12 months
                recency_warning = _check_assessment_recency(a.date_administered, a.assessment_name, max_age_months=12)
                if recency_warning:
                    warnings.append(recency_warning)

    if not data.skill_acquisition_targets:
        missing.append({"field": "skill_acquisition_targets", "description": ANTHEM_REQUIRED_FIELDS["skill_acquisition_targets"], "severity": "required"})

    if not data.behavior_reduction_targets:
        missing.append({"field": "behavior_reduction_targets", "description": ANTHEM_REQUIRED_FIELDS["behavior_reduction_targets"], "severity": "required"})
    else:
        for b in data.behavior_reduction_targets:
            if not b.operational_definition or len(b.operational_definition) < 20:
                warnings.append(f"Behavior '{b.behavior_name}' has a vague operational definition — high denial risk.")
            if b.baseline_value is None:
                warnings.append(f"Behavior '{b.behavior_name}' is missing baseline data — payors will flag this.")

    if not data.hours_utilization:
        missing.append({"field": "hours_utilization", "description": ANTHEM_REQUIRED_FIELDS["hours_utilization"], "severity": "required"})
    else:
        for h in data.hours_utilization:
            if h.utilization_pct and h.utilization_pct < 80 and not h.explanation_if_low:
                warnings.append(f"CPT {h.cpt_code.value}: utilization is {h.utilization_pct:.0f}% with no explanation — will trigger denial.")

    if not data.treatment_goals:
        missing.append({"field": "treatment_goals", "description": ANTHEM_REQUIRED_FIELDS["treatment_goals"], "severity": "required"})
    else:
        # Check for plateau without modification (Aetna terminates if no progress + no modification)
        for g in data.treatment_goals:
            if g.status in ("modified", "discontinued") and not g.modification_rationale:
                warnings.append(
                    f"Goal {g.goal_number} ('{g.goal_area}') is {g.status} but has no modification rationale — "
                    f"payors require justification for treatment changes."
                )

    if data.caregiver_training.total_sessions == 0:
        missing.append({"field": "caregiver_training", "description": ANTHEM_REQUIRED_FIELDS["caregiver_training.total_sessions"], "severity": "required"})

    if not data.discharge_plan.measurable_criteria:
        missing.append({"field": "discharge_plan", "description": ANTHEM_REQUIRED_FIELDS["discharge_plan.measurable_criteria"], "severity": "required"})

    # Calculate completeness score
    total_checks = len(ANTHEM_REQUIRED_FIELDS)
    required_missing = sum(1 for m in missing if m["severity"] == "required")
    score = (total_checks - required_missing) / total_checks

    return {
        "is_complete": required_missing == 0,
        "missing": missing,
        "warnings": warnings,
        "score": round(score, 2),
    }
