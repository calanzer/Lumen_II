"""ABA Authorization Agent — entrypoint: login, then page navigation."""

import streamlit as st
import streamlit_authenticator as stauth
import yaml
from pathlib import Path

from data.store import init_db
from ui_style import inject_custom_css, login_hero, sidebar_branding

st.set_page_config(
    page_title="Lumen ABA — Reauth Agent",
    page_icon="&#9672;",
    layout="wide",
    initial_sidebar_state="expanded",
)

inject_custom_css()

# Declared before the login gate so Streamlit never falls back to listing pages/
# for logged-out visitors; the nav stays hidden until authentication succeeds.
pg = st.navigation(
    [
        st.Page("pages/1_Clients.py", title="Clients", default=True),
        # Reached via View on the Clients page; needs a selected client, so no sidebar entry.
        st.Page("pages/2_Client_Detail.py", title="Client Detail", visibility="hidden"),
        st.Page("pages/3_Upload.py", title="Upload"),
        st.Page("pages/4_Review_Data.py", title="Review Data"),
        st.Page("pages/5_Generate.py", title="Generate"),
        st.Page("pages/6_Export.py", title="Export"),
        st.Page("pages/7_Templates.py", title="Templates"),
    ],
    position="sidebar" if st.session_state.get("authentication_status") is True else "hidden",
)

# --- Authentication ---
AUTH_CONFIG_PATH = Path(__file__).parent / ".streamlit" / "auth_config.yaml"

if AUTH_CONFIG_PATH.exists():
    with open(AUTH_CONFIG_PATH) as f:
        auth_config = yaml.safe_load(f)
else:
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

# --- Pre-login: branded landing ---
if st.session_state.get("authentication_status") is not True:
    login_hero()
    st.markdown("---")

authenticator.login()

if st.session_state.get("authentication_status") is False:
    st.error("Username or password is incorrect.")
    st.stop()
elif st.session_state.get("authentication_status") is None:
    st.warning("Please log in to continue.")
    st.markdown(
        '<p style="text-align:center; color:#6B7280; font-size:13px;">'
        'Default credentials: <code>bcba_reviewer</code> / <code>changeme</code>'
        '</p>',
        unsafe_allow_html=True,
    )
    st.stop()

# --- Authenticated content ---
sidebar_branding()
st.sidebar.write(f"Logged in as: **{st.session_state.get('name', '')}**")
authenticator.logout("Logout", "sidebar")
st.sidebar.markdown("---")

init_db()

pg.run()
