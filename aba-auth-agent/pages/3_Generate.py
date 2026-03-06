"""Page 3: Generate reauthorization narrative with BCBA review."""

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
        "Narrative will contain [CLINICIAN REVIEW NEEDED] placeholders for missing data."
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

# Display narrative sections for BCBA review
st.markdown("---")
st.subheader("BCBA Review — Edit Sections Below")
st.caption("This is an AI-generated draft. Review all sections before export. Your clinical judgment takes precedence.")

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
        edited = st.text_area(
            f"Edit {display_name}",
            value=section.content,
            height=200,
            key=f"edit_{field_name}",
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
