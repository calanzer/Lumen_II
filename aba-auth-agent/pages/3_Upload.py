"""Page 3: Upload progress report for a specific client/auth period."""

import streamlit as st
from datetime import date, timedelta
from dotenv import load_dotenv

load_dotenv()

from data.store import (
    get_client,
    get_auth_period,
    list_auth_periods,
    list_clients,
    create_auth_period,
    save_extraction,
)
from pipeline.classifier import classify_document
from pipeline.extractor import extract_clinical_data
from pipeline.validator import validate_completeness
from ui_style import (
    inject_custom_css,
    branded_header,
    sidebar_branding,
    sidebar_trust_badges,
    empty_state,
    metric_card,
    BRAND_PRIMARY,
    COLOR_SUCCESS,
    COLOR_WARNING,
    COLOR_INFO,
)

inject_custom_css()
sidebar_branding()
sidebar_trust_badges()

branded_header("Upload Progress Report", "Upload an ABA progress report to extract clinical data.")

# --- Client/Period Selection ---
client_id = st.session_state.get("selected_client_id")
period_id = st.session_state.get("selected_period_id")

# Client selector (if not pre-selected from dashboard)
clients = list_clients()
if not clients:
    empty_state(
        "&#128101;",
        "No clients found",
        "Go to Clients to add one first.",
    )
    st.stop()

client_names = {c["id"]: f"{c['display_name']} ({c.get('client_identifier') or 'no ID'})" for c in clients}
client_ids = list(client_names.keys())

default_idx = client_ids.index(client_id) if client_id in client_ids else 0
selected_client = st.selectbox(
    "Select Client",
    client_ids,
    index=default_idx,
    format_func=lambda x: client_names[x],
)
st.session_state.selected_client_id = selected_client

# Period selector or create new
periods = list_auth_periods(selected_client)
period_options = {p["id"]: f"{p['period_start']} to {p['period_end']} ({p['status']})" for p in periods}

col1, col2 = st.columns([3, 1])
with col1:
    if period_options:
        period_ids = list(period_options.keys())
        default_period_idx = period_ids.index(period_id) if period_id in period_ids else 0
        selected_period = st.selectbox(
            "Select Auth Period",
            period_ids,
            index=default_period_idx,
            format_func=lambda x: period_options[x],
        )
        st.session_state.selected_period_id = selected_period
    else:
        st.info("No auth periods exist for this client.")
        selected_period = None

with col2:
    st.write("")  # spacing
    st.write("")
    if st.button("+ New Period", type="primary"):
        today = date.today()
        new_id = create_auth_period(selected_client, today.isoformat(), (today + timedelta(days=182)).isoformat())
        st.session_state.selected_period_id = new_id
        st.rerun()

if not selected_period:
    st.stop()

st.divider()

# --- File Upload ---
@st.cache_data(show_spinner=False)
def cached_classify(file_bytes: bytes, filename: str) -> dict:
    return classify_document(file_bytes, filename)


@st.cache_data(show_spinner=False)
def cached_extract(file_bytes: bytes, filename: str):
    return extract_clinical_data(file_bytes, filename)


st.markdown(
    '<p style="font-size:14px; color:#6B7280; margin-bottom:4px;">'
    'Supported: PDF and DOCX from CentralReach, Catalyst, Rethink, or any ABA practice management system.'
    '</p>',
    unsafe_allow_html=True,
)

uploaded_file = st.file_uploader(
    "Upload an ABA progress report",
    type=["pdf", "docx"],
    label_visibility="collapsed",
)

if uploaded_file:
    file_bytes = uploaded_file.read()
    st.success(f"Uploaded: {uploaded_file.name} ({len(file_bytes) / 1024:.0f} KB)")

    # Classify
    with st.spinner("Analyzing document..."):
        classification = cached_classify(file_bytes, uploaded_file.name)

    col1, col2, col3 = st.columns(3)
    with col1:
        st.markdown(
            metric_card("Pages", classification["page_count"], BRAND_PRIMARY, "&#128196;"),
            unsafe_allow_html=True,
        )
    with col2:
        file_type_label = classification.get("file_type", "pdf").upper()
        type_text = f"{file_type_label} ({'Digital' if classification['is_native_digital'] else 'Scanned'})"
        st.markdown(
            metric_card("Type", type_text, COLOR_INFO, "&#128221;"),
            unsafe_allow_html=True,
        )
    with col3:
        st.markdown(
            metric_card("Source", classification["estimated_source"] or "Unknown", COLOR_INFO, "&#127968;"),
            unsafe_allow_html=True,
        )

    if not classification["is_native_digital"]:
        st.warning("This appears to be a scanned PDF. Extraction quality may be reduced.")

    st.markdown("<div style='height:12px;'></div>", unsafe_allow_html=True)

    if st.button("Extract Clinical Data", type="primary", use_container_width=True):
        with st.spinner("Extracting clinical data via Claude API... (30-60 seconds)"):
            try:
                clinical_data = cached_extract(file_bytes, uploaded_file.name)
                validation = validate_completeness(clinical_data)

                # Save to database
                save_extraction(selected_period, clinical_data, uploaded_file.name, validation)

                # Also put in session for immediate page navigation
                st.session_state.clinical_data = clinical_data
                st.session_state.validation = validation

                if validation["is_complete"]:
                    st.success(f"Extraction complete \u2014 all required fields found. Completeness: {validation['score']:.0%}")
                else:
                    st.warning(f"Extraction complete but missing {len(validation['missing'])} required fields. Completeness: {validation['score']:.0%}")

                if validation["warnings"]:
                    with st.expander(f"{len(validation['warnings'])} Warnings"):
                        for w in validation["warnings"]:
                            st.write(f"- {w}")

                st.info("Navigate to **Review Data** to verify and edit extracted data.")

                # Direct link to review
                if st.button("Go to Review \u2192", type="primary"):
                    st.switch_page("pages/4_Review_Data.py")

            except Exception as e:
                st.error(f"Extraction failed: {str(e)}")
                st.exception(e)

# Show existing extraction if period already has data
else:
    period = get_auth_period(selected_period)
    if period and period.get("extracted_data_parsed"):
        st.markdown(
            '<div style="background:#F0F7F9; padding:16px; border-radius:10px; border:1px solid #E6F4F7; margin:12px 0;">'
            f'<strong>This period already has extracted data</strong> from <em>{period.get("uploaded_filename", "unknown")}</em>.<br>'
            '<span style="color:#6B7280;">Upload a new file to re-extract, or continue to Review.</span>'
            '</div>',
            unsafe_allow_html=True,
        )
        if st.button("Go to Review \u2192", type="primary"):
            st.session_state.clinical_data = period["extracted_data_parsed"]
            st.session_state.validation = period.get("validation_result_parsed")
            st.switch_page("pages/4_Review_Data.py")
