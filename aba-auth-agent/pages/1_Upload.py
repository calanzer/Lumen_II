"""Page 1: Document Upload (PDF or DOCX) and Extraction"""

import streamlit as st
from dotenv import load_dotenv

load_dotenv()

from pipeline.classifier import classify_document
from pipeline.extractor import extract_clinical_data
from pipeline.validator import validate_completeness

st.header("Upload Progress Report")


@st.cache_data(show_spinner=False)
def cached_classify(file_bytes: bytes, filename: str) -> dict:
    """Cache document classification to avoid re-analysis on page reruns."""
    return classify_document(file_bytes, filename)


@st.cache_data(show_spinner=False)
def cached_extract(file_bytes: bytes, filename: str):
    """Cache extraction results to avoid redundant API calls on page reruns."""
    return extract_clinical_data(file_bytes, filename)


uploaded_file = st.file_uploader(
    "Upload an ABA progress report",
    type=["pdf", "docx"],
    help="Supported formats: PDF and DOCX. Works with CentralReach, Catalyst, Rethink, or any standard ABA progress report."
)

if uploaded_file:
    file_bytes = uploaded_file.read()
    st.session_state.pdf_bytes = file_bytes  # key kept for session compat
    st.session_state.uploaded_filename = uploaded_file.name
    st.success(f"Uploaded: {uploaded_file.name} ({len(file_bytes) / 1024:.0f} KB)")

    # Classify
    with st.spinner("Analyzing document..."):
        classification = cached_classify(file_bytes, uploaded_file.name)

    col1, col2, col3 = st.columns(3)
    col1.metric("Pages", classification["page_count"])
    file_type_label = classification.get("file_type", "pdf").upper()
    is_digital = classification["is_native_digital"]
    col2.metric("Type", f"{file_type_label} ({'Digital' if is_digital else 'Scanned'})")
    col3.metric("Source", classification["estimated_source"] or "Unknown")

    if not is_digital:
        st.warning("This appears to be a scanned PDF. Extraction quality may be reduced.")

    if st.button("Extract Clinical Data", type="primary"):
        with st.spinner("Extracting clinical data via Claude API... (this takes 30-60 seconds)"):
            try:
                clinical_data = cached_extract(file_bytes, uploaded_file.name)
                st.session_state.clinical_data = clinical_data

                # Run validation
                validation = validate_completeness(clinical_data)
                st.session_state.validation = validation

                if validation["is_complete"]:
                    st.success(f"Extraction complete — all required fields found. Completeness: {validation['score']:.0%}")
                else:
                    st.warning(f"Extraction complete but missing {len(validation['missing'])} required fields. Completeness: {validation['score']:.0%}")

                if validation["warnings"]:
                    with st.expander(f"{len(validation['warnings'])} Warnings"):
                        for w in validation["warnings"]:
                            st.write(f"- {w}")

                if validation["missing"]:
                    with st.expander(f"{len(validation['missing'])} Missing Required Fields"):
                        for m in validation["missing"]:
                            st.write(f"- **{m['field']}**: {m['description']}")

                st.info("Navigate to **Review Data** to verify and edit extracted data.")

            except Exception as e:
                st.error(f"Extraction failed: {str(e)}")
                st.exception(e)
