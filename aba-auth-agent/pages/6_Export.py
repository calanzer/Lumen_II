"""Page 6: Export narrative as Word document."""

import streamlit as st
from dotenv import load_dotenv

load_dotenv()

from data.store import get_auth_period, save_export, mark_submitted
from pipeline.exporter import export_to_docx, list_available_payors

st.header("Export Reauthorization Document")

# Load from DB
period_id = st.session_state.get("selected_period_id")

if period_id:
    period = get_auth_period(period_id)
    if period and period.get("extracted_data_parsed"):
        st.session_state.clinical_data = period["extracted_data_parsed"]
    if period and period.get("narrative_data_parsed"):
        st.session_state.narrative = period["narrative_data_parsed"]

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
        f"{review_needed} section(s) still need review. "
        "Ensure these are resolved before submitting to the payor."
    )

# Payor template selector
st.subheader("Select Payor Template")
payors = list_available_payors()
payor_options = {key: f"{info['display_name']} — {info['subtitle']}" for key, info in payors.items()}
selected_payor = st.selectbox(
    "Choose the payor template for your Word document:",
    options=list(payor_options.keys()),
    format_func=lambda k: payor_options[k],
    index=0,
)

if not payors[selected_payor]["template_exists"]:
    st.info(f"A default template will be auto-generated for {payors[selected_payor]['display_name']}. "
            "You can replace it with a custom .docx template in the `templates/` directory.")

# AI Disclosure checkbox
confirmed = st.checkbox(
    "I have reviewed all sections and confirm this document is clinically accurate.",
    value=False,
)

if st.button("Generate Word Document", type="primary", disabled=not confirmed):
    with st.spinner("Building Word document..."):
        try:
            docx_bytes = export_to_docx(data, narrative, payor_key=selected_payor)
            st.session_state.docx_bytes = docx_bytes

            payor_short = selected_payor.replace("_", "-")
            filename = f"reauth_{payor_short}_{data.client.client_id or 'client'}_{data.client.auth_period_end or 'draft'}.docx"

            st.download_button(
                label="Download DOCX",
                data=docx_bytes,
                file_name=filename,
                mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
            )
            st.success(f"Document ready: {filename}")

            # Mark as exported in DB
            if period_id:
                save_export(period_id)

        except Exception as e:
            st.error(f"Export failed: {e}")
            st.exception(e)

# Post-export: mark as submitted
if period_id:
    period = get_auth_period(period_id)
    if period and period.get("status") == "exported":
        st.divider()
        st.subheader("After Submitting to Payor")
        st.caption("Once you've submitted this document to the payor, mark it here to update your dashboard.")
        if st.button("Mark as Submitted to Payor", use_container_width=True):
            mark_submitted(period_id)
            st.success("Status updated to Submitted.")
            st.rerun()
