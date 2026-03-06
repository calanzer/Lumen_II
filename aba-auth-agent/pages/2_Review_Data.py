"""Page 2: Review and edit extracted clinical data."""

import streamlit as st
import json

st.header("Review Extracted Data")

if st.session_state.get("clinical_data") is None:
    st.warning("No data extracted yet. Go to **Upload** first.")
    st.stop()

data = st.session_state.clinical_data

# Display as editable JSON — MVP approach. Production would use per-field forms.
st.subheader("Client Demographics")
st.json(data.client.model_dump(mode="json"), expanded=True)

st.subheader(f"Assessments ({len(data.assessments)})")
for i, a in enumerate(data.assessments):
    with st.expander(f"{a.assessment_type.value}: {a.assessment_name}"):
        st.json(a.model_dump(mode="json"))

st.subheader(f"Skill Acquisition Targets ({len(data.skill_acquisition_targets)})")
mastered = sum(1 for t in data.skill_acquisition_targets if t.is_mastered)
st.metric("Mastered", f"{mastered} / {len(data.skill_acquisition_targets)}")
for i, t in enumerate(data.skill_acquisition_targets):
    status = "Mastered" if t.is_mastered else "In Progress"
    with st.expander(f"[{status}] {t.domain}: {t.target_name}"):
        st.json(t.model_dump(mode="json"))

st.subheader(f"Behavior Reduction Targets ({len(data.behavior_reduction_targets)})")
for i, b in enumerate(data.behavior_reduction_targets):
    trend_label = b.trend.value if b.trend else "unknown"
    with st.expander(f"[{trend_label}] {b.behavior_name}"):
        st.json(b.model_dump(mode="json"))

st.subheader(f"Hours Utilization ({len(data.hours_utilization)})")
for h in data.hours_utilization:
    pct = h.utilization_pct or (h.utilized_units / h.authorized_units * 100 if h.authorized_units else 0)
    st.write(f"**{h.cpt_code.value}**: {h.utilized_units}/{h.authorized_units} units ({pct:.0f}%)")

st.subheader(f"Treatment Goals ({len(data.treatment_goals)})")
for g in data.treatment_goals:
    with st.expander(f"Goal {g.goal_number}: {g.goal_area} — {g.status}"):
        st.json(g.model_dump(mode="json"))

st.subheader("Caregiver Training")
st.json(data.caregiver_training.model_dump(mode="json"))

st.subheader("Discharge Plan")
st.json(data.discharge_plan.model_dump(mode="json"))

# Full JSON editor for power users
with st.expander("Edit Raw JSON (Advanced)"):
    edited_json = st.text_area(
        "Edit the full extracted data JSON:",
        value=json.dumps(data.model_dump(mode="json"), indent=2, default=str),
        height=400,
    )
    if st.button("Save Edits"):
        try:
            from schemas.clinical_data import ExtractedClinicalData
            updated = ExtractedClinicalData.model_validate_json(edited_json)
            st.session_state.clinical_data = updated
            st.success("Data updated successfully.")
        except Exception as e:
            st.error(f"Invalid JSON: {e}")

if data.confidence_notes:
    st.subheader("Extraction Confidence Notes")
    for note in data.confidence_notes:
        st.write(f"- {note}")

if data.missing_fields:
    st.subheader("Missing Fields")
    for field in data.missing_fields:
        st.write(f"- {field}")

st.info("When data looks correct, navigate to **Generate** to create the reauthorization narrative.")
