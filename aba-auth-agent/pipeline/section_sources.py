"""Which extracted data each narrative section was written from, for side-by-side review.

The built-in nine-section layout has a fixed mapping. Template-driven narratives carry the
field names the model said it used (`source_data_keys`) in each section.
"""

import json
from typing import Callable

from schemas.clinical_data import ExtractedClinicalData
from schemas.narrative import CustomNarrative, Narrative, NarrativeSection


def _dump(items) -> list:
    return [item.model_dump(mode="json") for item in items]


SECTION_SOURCES: dict[str, Callable[[ExtractedClinicalData], dict]] = {
    "client_overview": lambda d: {"client": d.client.model_dump(mode="json")},
    "assessment_summary": lambda d: {"assessments": _dump(d.assessments)},
    "skill_acquisition_progress": lambda d: {"skill_acquisition_targets": _dump(d.skill_acquisition_targets)},
    "behavior_reduction_progress": lambda d: {"behavior_reduction_targets": _dump(d.behavior_reduction_targets)},
    "treatment_plan_update": lambda d: {"treatment_goals": _dump(d.treatment_goals)},
    "hours_justification": lambda d: {
        "hours_utilization": _dump(d.hours_utilization),
        "requested_hours_by_code": d.requested_hours_by_code,
        "clinical_justification_for_hours": d.clinical_justification_for_hours,
    },
    "caregiver_training_summary": lambda d: {"caregiver_training": d.caregiver_training.model_dump(mode="json")},
    "medical_necessity": lambda d: {
        "client_diagnosis": d.client.diagnosis_codes,
        "assessments_summary": [
            {"name": a.assessment_name, "standard_score": a.standard_score, "percentile": a.percentile}
            for a in d.assessments
        ],
        "behavior_trends": [
            {
                "name": b.behavior_name,
                "trend": b.trend.value if b.trend else None,
                "baseline": b.baseline_value,
                "current": b.current_value,
            }
            for b in d.behavior_reduction_targets
        ],
    },
    "discharge_plan": lambda d: {"discharge_plan": d.discharge_plan.model_dump(mode="json")},
}


def source_for_section(narrative: Narrative, key: str, section: NarrativeSection, data: ExtractedClinicalData) -> dict:
    """The extracted data behind one section (JSON-safe; empty when the AI named no fields)."""
    if not isinstance(narrative, CustomNarrative) and key in SECTION_SOURCES:
        source = SECTION_SOURCES[key](data)
    else:
        dumped = json.loads(data.model_dump_json())
        source = {k: dumped[k] for k in section.source_data_keys if k in dumped}
    return json.loads(json.dumps(source, default=str))
