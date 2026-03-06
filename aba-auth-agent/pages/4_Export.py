"""Page 4: Export narrative as Word document."""

import streamlit as st
from dotenv import load_dotenv

load_dotenv()

from pipeline.exporter import export_to_docx

st.header("Export Reauthorization Document")

if st.session_state.get("narrative") is None:
    st.warning("No narrative generated yet. Go to **Generate** first.")
    st.stop()

data = st.session_state.clinical_data
narrative = st.session_state.narrative

# Show summary before export
st.subheader("Export Summary")
col1, col2, col3 = st.columns(3)
col1.metric("Confidence", f"{narrative.overall_confidence:.0%}")
col2.metric("Flags", len(narrative.flags_for_bcba))

review_needed = sum(
    1 for section_name in [
        "client_overview", "assessment_summary", "skill_acquisition_progress",
        "behavior_reduction_progress", "treatment_plan_update", "hours_justification",
        "caregiver_training_summary", "medical_necessity", "discharge_plan",
    ]
    if getattr(narrative, section_name).requires_review
)
col3.metric("Sections Needing Review", review_needed)

if review_needed > 0:
    st.warning(
        f"{review_needed} section(s) still contain [CLINICIAN REVIEW NEEDED] placeholders. "
        "Ensure these are resolved before submitting to the payor."
    )

# AI Disclosure checkbox
confirmed = st.checkbox(
    "I have reviewed all sections and confirm this document is clinically accurate.",
    value=False,
)

if st.button("Generate Word Document", type="primary", disabled=not confirmed):
    with st.spinner("Building Word document..."):
        try:
            docx_bytes = export_to_docx(data, narrative)
            st.session_state.docx_bytes = docx_bytes

            filename = f"reauth_{data.client.client_id or 'client'}_{data.client.auth_period_end or 'draft'}.docx"

            st.download_button(
                label="Download DOCX",
                data=docx_bytes,
                file_name=filename,
                mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
            )
            st.success(f"Document ready: {filename}")

        except Exception as e:
            st.error(f"Export failed: {e}")
            st.exception(e)
