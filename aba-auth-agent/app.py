"""ABA Authorization Agent — MVP Prototype"""

import streamlit as st
import streamlit_authenticator as stauth
import yaml
from pathlib import Path

st.set_page_config(
    page_title="ABA Auth Agent",
    page_icon="📋",
    layout="wide",
    initial_sidebar_state="expanded",
)

# --- Authentication ---
# Load or create auth config
AUTH_CONFIG_PATH = Path(__file__).parent / ".streamlit" / "auth_config.yaml"

if AUTH_CONFIG_PATH.exists():
    with open(AUTH_CONFIG_PATH) as f:
        auth_config = yaml.safe_load(f)
else:
    # Default config for validation phase — single BCBA user
    # Password: "changeme" (hashed with bcrypt)
    import bcrypt
    default_hash = bcrypt.hashpw("changeme".encode(), bcrypt.gensalt()).decode()
    auth_config = {
        "credentials": {
            "usernames": {
                "bcba_reviewer": {
                    "name": "BCBA Reviewer",
                    "password": default_hash,
                }
            }
        },
        "cookie": {
            "name": "aba_auth_agent",
            "key": "aba_auth_agent_signature_key",
            "expiry_days": 7,
        },
    }
    AUTH_CONFIG_PATH.parent.mkdir(parents=True, exist_ok=True)
    with open(AUTH_CONFIG_PATH, "w") as f:
        yaml.dump(auth_config, f)

authenticator = stauth.Authenticate(
    auth_config["credentials"],
    auth_config["cookie"]["name"],
    auth_config["cookie"]["key"],
    auth_config["cookie"]["expiry_days"],
)

authenticator.login()

if st.session_state.get("authentication_status") is False:
    st.error("Username or password is incorrect.")
    st.stop()
elif st.session_state.get("authentication_status") is None:
    st.warning("Please log in to continue.")
    st.info("Default credentials for validation: username `bcba_reviewer`, password `changeme`")
    st.stop()

# --- Authenticated content ---
st.sidebar.write(f"Logged in as: **{st.session_state.get('name', '')}**")
authenticator.logout("Logout", "sidebar")

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
