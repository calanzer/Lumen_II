"""ABA Authorization Agent — Client Dashboard"""

import streamlit as st
import streamlit_authenticator as stauth
import yaml
from datetime import date
from pathlib import Path

from data.store import get_dashboard_data, init_db

st.set_page_config(
    page_title="ABA Auth Agent",
    page_icon="📋",
    layout="wide",
    initial_sidebar_state="expanded",
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

authenticator.login()

if st.session_state.get("authentication_status") is False:
    st.error("Username or password is incorrect.")
    st.stop()
elif st.session_state.get("authentication_status") is None:
    st.warning("Please log in to continue.")
    st.stop()

# --- Authenticated content ---
st.sidebar.write(f"Logged in as: **{st.session_state.get('name', '')}**")
authenticator.logout("Logout", "sidebar")

init_db()

st.title("ABA Authorization Agent")

# --- Dashboard ---
dashboard = get_dashboard_data()

if not dashboard:
    st.info("No clients yet. Go to **Clients** to add your first client.")
    st.stop()

# Summary metrics
total = len(dashboard)
critical = sum(1 for d in dashboard if d["urgency"] == "critical")
soon = sum(1 for d in dashboard if d["urgency"] == "soon")
expired = sum(1 for d in dashboard if d["urgency"] == "expired")
in_progress = sum(1 for d in dashboard if d.get("period_status") in ("in_progress", "generated"))

col1, col2, col3, col4, col5 = st.columns(5)
col1.metric("Total Clients", total)
col2.metric("Expired", expired, delta=None)
col3.metric("Due < 14 days", critical, delta=None)
col4.metric("Due < 30 days", soon, delta=None)
col5.metric("In Progress", in_progress)

st.divider()

# Search and filter
filter_col1, filter_col2 = st.columns([2, 1])
with filter_col1:
    search_query = st.text_input(
        "Search clients", placeholder="Search by name or ID...",
        label_visibility="collapsed", key="dashboard_search",
    )
with filter_col2:
    urgency_filter = st.selectbox(
        "Filter", ["All", "Needs Attention", "Expired", "Due Soon", "In Progress"],
        label_visibility="collapsed", key="dashboard_filter",
    )

# Apply filters
filtered = dashboard
if search_query:
    q = search_query.lower()
    filtered = [d for d in filtered if q in d["display_name"].lower() or q in (d.get("client_identifier") or "").lower()]
if urgency_filter == "Needs Attention":
    filtered = [d for d in filtered if d["urgency"] in ("expired", "critical", "soon")]
elif urgency_filter == "Expired":
    filtered = [d for d in filtered if d["urgency"] == "expired"]
elif urgency_filter == "Due Soon":
    filtered = [d for d in filtered if d["urgency"] in ("critical", "soon")]
elif urgency_filter == "In Progress":
    filtered = [d for d in filtered if d.get("period_status") in ("in_progress", "generated")]

if not filtered:
    st.info("No clients match your search." if search_query else "No clients match this filter.")
    st.stop()

# Client table
URGENCY_ICONS = {
    "expired": "🔴",
    "critical": "🔴",
    "soon": "🟡",
    "ok": "🟢",
    "no_period": "⚪",
}

STATUS_LABELS = {
    "draft": "Draft",
    "in_progress": "Reviewing",
    "generated": "Narrative Ready",
    "exported": "Exported",
    "submitted": "Submitted",
    None: "—",
}

for d in filtered:
    icon = URGENCY_ICONS.get(d["urgency"], "⚪")
    status_label = STATUS_LABELS.get(d.get("period_status"), "—")
    dx = ", ".join(d["diagnosis_codes"][:2]) if d["diagnosis_codes"] else "—"

    if d["period_end"]:
        days = d["days_until_expiry"]
        if days < 0:
            expiry_text = f"Expired {abs(days)}d ago"
        else:
            expiry_text = f"{days}d remaining"
    else:
        expiry_text = "No auth period"

    col_icon, col_name, col_dx, col_expiry, col_status, col_action = st.columns([0.5, 2, 1.5, 1.5, 1.5, 1.5])

    with col_icon:
        st.write(icon)
    with col_name:
        st.write(f"**{d['display_name']}**")
        if d["client_identifier"]:
            st.caption(d["client_identifier"])
    with col_dx:
        st.write(dx)
    with col_expiry:
        st.write(expiry_text)
    with col_status:
        st.write(status_label)
    with col_action:
        if d.get("period_id"):
            if st.button("Open", key=f"open_{d['client_id']}", use_container_width=True):
                st.session_state.selected_client_id = d["client_id"]
                st.session_state.selected_period_id = d["period_id"]
                st.switch_page("pages/2_Client_Detail.py")
        else:
            if st.button("Set Up", key=f"setup_{d['client_id']}", use_container_width=True):
                st.session_state.selected_client_id = d["client_id"]
                st.switch_page("pages/2_Client_Detail.py")
