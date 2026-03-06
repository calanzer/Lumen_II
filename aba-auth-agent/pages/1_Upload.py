"""Page 1: PDF Upload and Extraction"""

import streamlit as st
from dotenv import load_dotenv

load_dotenv()

from pipeline.classifier import classify_pdf
from pipeline.extractor import extract_clinical_data
from pipeline.validator import validate_completeness

st.header("Upload Progress Report")


@st.cache_data(show_spinner=False)
def cached_classify(pdf_bytes: bytes) -> dict:
    """Cache PDF classification to avoid re-analysis on page reruns."""
    return classify_pdf(pdf_bytes)


@st.cache_data(show_spinner=False)
def cached_extract(pdf_bytes: bytes, filename: str):
    """Cache extraction results to avoid redundant API calls on page reruns."""
    return extract_clinical_data(pdf_bytes, filename)


uploaded_file = st.file_uploader(
    "Upload an ABA progress report PDF",
    type=["pdf"],
    help="Supported: CentralReach, Catalyst, Rethink, or any standard ABA progress report PDF."
)

if uploaded_file:
    pdf_bytes = uploaded_file.read()
    st.session_state.pdf_bytes = pdf_bytes
    st.success(f"Uploaded: {uploaded_file.name} ({len(pdf_bytes) / 1024:.0f} KB)")

    # Classify
    with st.spinner("Analyzing PDF..."):
        classification = cached_classify(pdf_bytes)

    col1, col2, col3 = st.columns(3)
    col1.metric("Pages", classification["page_count"])
    col2.metric("Type", "Digital" if classification["is_native_digital"] else "Scanned")
    col3.metric("Source", classification["estimated_source"] or "Unknown")

    if not classification["is_native_digital"]:
        st.warning("This appears to be a scanned PDF. Extraction quality may be reduced.")

    if st.button("Extract Clinical Data", type="primary"):
        with st.spinner("Extracting clinical data via Claude API... (this takes 30-60 seconds)"):
            try:
                clinical_data = cached_extract(pdf_bytes, uploaded_file.name)
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
