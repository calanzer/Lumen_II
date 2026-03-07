"""Page 5: Generate reauthorization narrative with BCBA review.

Provides side-by-side view of source data and generated narrative for each section.
BCBAs can edit every narrative section directly. Edits persist to DB.
Shows prior period data for comparison when available.
"""

import json

import streamlit as st
from dotenv import load_dotenv

load_dotenv()

from data.store import get_auth_period, get_prior_period, save_narrative
from pipeline.generator import generate_narrative, validate_narrative_against_source
from schemas.narrative import AnthemReauthNarrative

st.header("Generate Reauthorization Narrative")

# Load from DB
period_id = st.session_state.get("selected_period_id")
client_id = st.session_state.get("selected_client_id")

if period_id:
    period = get_auth_period(period_id)
    if period and period.get("extracted_data_parsed"):
        st.session_state.clinical_data = period["extracted_data_parsed"]
        if period.get("validation_result_parsed"):
            st.session_state.validation = period["validation_result_parsed"]
    if period and period.get("narrative_data_parsed"):
        st.session_state.narrative = period["narrative_data_parsed"]

if st.session_state.get("clinical_data") is None:
    st.warning("No data extracted yet. Go to **Upload** first.")
    st.stop()

data = st.session_state.clinical_data

# Prior period comparison
prior_period = None
if period_id and client_id:
    prior_period = get_prior_period(client_id, period_id)

if prior_period and prior_period.get("extracted_data_parsed"):
    with st.expander("Prior Period Comparison", expanded=False):
        prior_data = prior_period["extracted_data_parsed"]
        st.caption(f"Comparing against: {prior_period['period_start']} to {prior_period['period_end']}")

        col1, col2 = st.columns(2)
        with col1:
            st.write("**Prior Period:**")
            st.write(f"- Skill targets: {len(prior_data.skill_acquisition_targets)} ({sum(1 for t in prior_data.skill_acquisition_targets if t.is_mastered)} mastered)")
            st.write(f"- Behaviors: {len(prior_data.behavior_reduction_targets)}")
            for b in prior_data.behavior_reduction_targets:
                if b.current_value is not None:
                    st.write(f"  - {b.behavior_name}: {b.current_value} {b.unit}")
        with col2:
            st.write("**Current Period:**")
            st.write(f"- Skill targets: {len(data.skill_acquisition_targets)} ({sum(1 for t in data.skill_acquisition_targets if t.is_mastered)} mastered)")
            st.write(f"- Behaviors: {len(data.behavior_reduction_targets)}")
            for b in data.behavior_reduction_targets:
                if b.current_value is not None:
                    st.write(f"  - {b.behavior_name}: {b.current_value} {b.unit}")

# Check validation status
validation = st.session_state.get("validation", {})
if not validation.get("is_complete", False):
    st.warning(
        f"Extracted data is incomplete (score: {validation.get('score', 0):.0%}). "
        "Narrative will contain placeholders for missing data."
    )

if st.button("Generate Anthem Blue Cross Narrative", type="primary"):
    with st.spinner("Generating narrative... (30-60 seconds)"):
        try:
            narrative = generate_narrative(data)
            st.session_state.narrative = narrative
            # Save to DB
            if period_id:
                save_narrative(period_id, narrative)
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
st.subheader("BCBA Review — Edit Narrative Sections")
st.caption(
    "Left: source data for verification. Right: AI-generated draft — **edit directly in the text boxes**. "
    "Your clinical judgment takes precedence over AI output."
)

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

for field_name, display_name in sections:
    section = getattr(narrative, field_name)
    flag = "⚠ " if section.requires_review else ""
    with st.expander(f"{flag}{display_name}", expanded=section.requires_review):
        if section.requires_review and section.review_note:
            st.warning(f"Review needed: {section.review_note}")

        # Side-by-side: source data (left) | narrative editor (right)
        col_source, col_narrative = st.columns(2)

        with col_source:
            st.caption("Source Data (read-only reference)")
            source_fn = SECTION_SOURCE_MAP.get(field_name)
            if source_fn:
                source_data = source_fn(data)
                st.json(json.loads(json.dumps(source_data, default=str)))

        with col_narrative:
            st.caption("Narrative (edit below)")
            edited = st.text_area(
                f"Edit {display_name}",
                value=section.content,
                height=250,
                key=f"edit_{field_name}",
                label_visibility="collapsed",
            )
            section.content = edited

            word_count = len(edited.split())
            if word_count < 50:
                st.caption(f"⚠ {word_count} words — may be too brief for payor")
            elif word_count > 400:
                st.caption(f"⚠ {word_count} words — consider condensing")
            else:
                st.caption(f"{word_count} words")

# Show flags
if narrative.flags_for_bcba:
    st.subheader("Items Requiring BCBA Attention")
    for flag_text in narrative.flags_for_bcba:
        st.write(f"- {flag_text}")

st.markdown("---")

# Save & continue
col1, col2 = st.columns([2, 1])
with col1:
    if st.button("Save All Edits", type="primary", use_container_width=True):
        st.session_state.narrative = narrative
        if period_id:
            save_narrative(period_id, narrative)
        st.toast("All narrative edits saved.", icon="✅")
        st.success("Edits saved. Navigate to **Export** to download as Word document.")

with col2:
    st.page_link("pages/6_Export.py", label="Continue to Export →", use_container_width=True)
