"""Page 6: Export narrative as Word document."""

import streamlit as st
from dotenv import load_dotenv

load_dotenv()

from data.store import get_auth_period, save_export
from pipeline.exporter import export_to_docx, list_available_payors
from ui_style import (
    inject_custom_css,
    branded_header,
    sidebar_branding,
    sidebar_trust_badges,
    metric_card,
    status_badge,
    progress_bar_html,
    COLOR_SUCCESS,
    COLOR_WARNING,
    COLOR_CRITICAL,
    COLOR_INFO,
    BRAND_PRIMARY,
)

inject_custom_css()
sidebar_branding()
sidebar_trust_badges()

branded_header("Export Reauthorization Document", "Review summary and download as Word document for payor submission.")

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
st.markdown(
    '<div class="section-header">'
    '<span class="section-title">Export Summary</span>'
    '</div>',
    unsafe_allow_html=True,
)

confidence_color = COLOR_SUCCESS if narrative.overall_confidence >= 0.8 else COLOR_WARNING

review_needed = sum(
    1 for section_name in [
        "client_overview", "assessment_summary", "skill_acquisition_progress",
        "behavior_reduction_progress", "treatment_plan_update", "hours_justification",
        "caregiver_training_summary", "medical_necessity", "discharge_plan",
    ]
    if getattr(narrative, section_name).requires_review
)

review_color = COLOR_SUCCESS if review_needed == 0 else COLOR_WARNING
flags_color = COLOR_SUCCESS if len(narrative.flags_for_bcba) == 0 else COLOR_WARNING

col1, col2, col3 = st.columns(3)
with col1:
    st.markdown(
        '<div class="metric-card" style="border-left: 4px solid ' + confidence_color + ';">'
        '<div class="card-label">CONFIDENCE</div>'
        '<div class="card-value">' + f'{narrative.overall_confidence:.0%}' + '</div>'
        '<div style="margin-top:6px;">'
        + progress_bar_html(narrative.overall_confidence * 100, 100, confidence_color)
        + '</div></div>',
        unsafe_allow_html=True,
    )
with col2:
    st.markdown(
        metric_card("BCBA Flags", len(narrative.flags_for_bcba), flags_color, "&#9888;"),
        unsafe_allow_html=True,
    )
with col3:
    st.markdown(
        metric_card("Sections Needing Review", review_needed, review_color, "&#128221;"),
        unsafe_allow_html=True,
    )

if review_needed > 0:
    st.markdown(
        f'<div style="background:#FFFBEB; border:1px solid #FDE68A; border-radius:10px; padding:14px 18px; margin:16px 0;">'
        f'<strong style="color:#D97706;">{review_needed} section(s) still need review.</strong> '
        f'Ensure these are resolved before submitting to the payor.'
        f'</div>',
        unsafe_allow_html=True,
    )

st.markdown("<div style='height:16px;'></div>", unsafe_allow_html=True)

# Payor template selector
st.markdown(
    '<div class="section-header">'
    '<span class="section-title">Select Payor Template</span>'
    '</div>',
    unsafe_allow_html=True,
)

payors = list_available_payors()
payor_options = {key: f"{info['display_name']} \u2014 {info['subtitle']}" for key, info in payors.items()}
selected_payor = st.selectbox(
    "Choose the payor template for your Word document:",
    options=list(payor_options.keys()),
    format_func=lambda k: payor_options[k],
    index=0,
)

if not payors[selected_payor]["template_exists"]:
    st.info(f"A default template will be auto-generated for {payors[selected_payor]['display_name']}. "
            "You can replace it with a custom .docx template in the `templates/` directory.")

st.markdown("<div style='height:16px;'></div>", unsafe_allow_html=True)

# AI Disclosure checkbox with styled container
st.markdown(
    '<div style="background:#F0F7F9; border:1px solid #E6F4F7; border-radius:10px; padding:16px 18px; margin-bottom:16px;">',
    unsafe_allow_html=True,
)
confirmed = st.checkbox(
    "I have reviewed all sections and confirm this document is clinically accurate.",
    value=False,
)
st.markdown('</div>', unsafe_allow_html=True)

if st.button("Generate Word Document", type="primary", disabled=not confirmed, use_container_width=True):
    with st.spinner("Building Word document..."):
        try:
            docx_bytes = export_to_docx(data, narrative, payor_key=selected_payor)
            st.session_state.docx_bytes = docx_bytes

            payor_short = selected_payor.replace("_", "-")
            filename = f"reauth_{payor_short}_{data.client.client_id or 'client'}_{data.client.auth_period_end or 'draft'}.docx"

            st.markdown("<div style='height:12px;'></div>", unsafe_allow_html=True)

            st.download_button(
                label="Download DOCX",
                data=docx_bytes,
                file_name=filename,
                mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
                use_container_width=True,
            )

            st.markdown(
                f'<div style="background:#ECFDF5; border:1px solid #A7F3D0; border-radius:10px; padding:14px 18px; margin-top:12px;">'
                f'<strong style="color:#059669;">Document ready:</strong> {filename}'
                f'</div>',
                unsafe_allow_html=True,
            )

            # Mark as exported in DB
            if period_id:
                save_export(period_id)

        except Exception as e:
            st.error(f"Export failed: {e}")
            st.exception(e)
