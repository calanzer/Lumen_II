"""Page 3: Generate reauthorization narrative with BCBA review.

Provides side-by-side view of source data and generated narrative for each section,
enabling BCBAs to verify accuracy against the original extraction.
"""

import json

import streamlit as st
from dotenv import load_dotenv

load_dotenv()

from pipeline.generator import generate_narrative, validate_narrative_against_source

st.header("Generate Reauthorization Narrative")

if st.session_state.get("clinical_data") is None:
    st.warning("No data extracted yet. Go to **Upload** first.")
    st.stop()

data = st.session_state.clinical_data

# Check validation status
validation = st.session_state.get("validation", {})
if not validation.get("is_complete", False):
    st.warning(
        f"Extracted data is incomplete (score: {validation.get('score', 0):.0%}). "
        "Narrative will contain [DATA NOT PROVIDED — CLINICIAN ACTION REQUIRED] placeholders for missing data."
    )

if st.button("Generate Anthem Blue Cross Narrative", type="primary"):
    with st.spinner("Generating narrative... (30-60 seconds)"):
        try:
            narrative = generate_narrative(data)
            st.session_state.narrative = narrative
            st.success(f"Narrative generated. Confidence: {narrative.overall_confidence:.0%}")
        except Exception as e:
            st.error(f"Generation failed: {e}")
            st.exception(e)
            st.stop()

    # Post-generation validation
    with st.spinner("Cross-validating against source data..."):
        discrepancies = validate_narrative_against_source(narrative, data)
        if discrepancies:
            st.warning(f"{len(discrepancies)} potential discrepancies found:")
            for d in discrepancies:
                st.write(d)
        else:
            st.success("No discrepancies detected in cross-validation.")

if st.session_state.get("narrative") is None:
    st.stop()

narrative = st.session_state.narrative

# Display narrative sections for BCBA review with side-by-side source data
st.markdown("---")
st.subheader("BCBA Review — Side-by-Side Comparison")
st.caption("This is an AI-generated draft. Source data is shown on the left for verification. Your clinical judgment takes precedence.")

# Map sections to their relevant source data fields for side-by-side display
SECTION_SOURCE_MAP = {
    "client_overview": lambda d: {
        "client": d.client.model_dump(mode="json"),
    },
    "assessment_summary": lambda d: {
        "assessments": [a.model_dump(mode="json") for a in d.assessments],
    },
    "skill_acquisition_progress": lambda d: {
        "skill_acquisition_targets": [t.model_dump(mode="json") for t in d.skill_acquisition_targets],
    },
    "behavior_reduction_progress": lambda d: {
        "behavior_reduction_targets": [b.model_dump(mode="json") for b in d.behavior_reduction_targets],
    },
    "treatment_plan_update": lambda d: {
        "treatment_goals": [g.model_dump(mode="json") for g in d.treatment_goals],
    },
    "hours_justification": lambda d: {
        "hours_utilization": [h.model_dump(mode="json") for h in d.hours_utilization],
        "requested_hours_by_code": d.requested_hours_by_code,
        "clinical_justification_for_hours": d.clinical_justification_for_hours,
    },
    "caregiver_training_summary": lambda d: {
        "caregiver_training": d.caregiver_training.model_dump(mode="json"),
    },
    "medical_necessity": lambda d: {
        "client_diagnosis": d.client.diagnosis_codes,
        "assessments_summary": [
            {"name": a.assessment_name, "standard_score": a.standard_score, "percentile": a.percentile}
            for a in d.assessments
        ],
        "behavior_trends": [
            {"name": b.behavior_name, "trend": b.trend.value if b.trend else None, "baseline": b.baseline_value, "current": b.current_value}
            for b in d.behavior_reduction_targets
        ],
    },
    "discharge_plan": lambda d: {
        "discharge_plan": d.discharge_plan.model_dump(mode="json"),
    },
}

sections = [
    ("client_overview", "1. Client Overview"),
    ("assessment_summary", "2. Assessment Summary"),
    ("skill_acquisition_progress", "3. Skill Acquisition Progress"),
    ("behavior_reduction_progress", "4. Behavior Reduction Progress"),
    ("treatment_plan_update", "5. Treatment Plan Update"),
    ("hours_justification", "6. Hours Utilization & Justification"),
    ("caregiver_training_summary", "7. Caregiver Training"),
    ("medical_necessity", "8. Medical Necessity Statement"),
    ("discharge_plan", "9. Discharge Plan"),
]

edited_sections = {}
for field_name, display_name in sections:
    section = getattr(narrative, field_name)
    flag = "[REVIEW] " if section.requires_review else ""
    with st.expander(f"{flag}{display_name}", expanded=section.requires_review):
        if section.requires_review and section.review_note:
            st.warning(f"Review needed: {section.review_note}")

        # Side-by-side: source data (left) | narrative editor (right)
        col_source, col_narrative = st.columns(2)

        with col_source:
            st.caption("Source Data")
            source_fn = SECTION_SOURCE_MAP.get(field_name)
            if source_fn:
                source_data = source_fn(data)
                st.json(json.loads(json.dumps(source_data, default=str)))
            else:
                st.info("No source data mapping for this section.")

        with col_narrative:
            st.caption("Generated Narrative (editable)")
            edited = st.text_area(
                f"Edit {display_name}",
                value=section.content,
                height=250,
                key=f"edit_{field_name}",
                label_visibility="collapsed",
            )
            edited_sections[field_name] = edited

# Show flags
if narrative.flags_for_bcba:
    st.subheader("Items Requiring Attention")
    for flag in narrative.flags_for_bcba:
        st.write(f"- {flag}")

# Save edits back
if st.button("Save All Edits"):
    for field_name, content in edited_sections.items():
        section = getattr(narrative, field_name)
        section.content = content
    st.session_state.narrative = narrative
    st.success("All edits saved. Navigate to **Export** to download as Word document.")
