"""ABA Authorization Agent — MVP Prototype"""

import streamlit as st

st.set_page_config(
    page_title="ABA Auth Agent",
    page_icon="📋",
    layout="wide",
    initial_sidebar_state="expanded",
)

st.title("ABA Authorization Agent")
st.markdown("**MVP Prototype** — Anthem Blue Cross CA Reauthorizations")
st.markdown("---")
st.markdown(
    "Use the sidebar to navigate through the workflow:\n\n"
    "1. **Upload** — Upload a progress report PDF\n"
    "2. **Review Data** — Verify extracted clinical data\n"
    "3. **Generate** — Create reauthorization narrative\n"
    "4. **Export** — Download as Word document"
)

# Initialize session state
if "clinical_data" not in st.session_state:
    st.session_state.clinical_data = None
if "narrative" not in st.session_state:
    st.session_state.narrative = None
if "pdf_bytes" not in st.session_state:
    st.session_state.pdf_bytes = None
