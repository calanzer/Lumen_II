"""ABA Authorization Agent — Client Dashboard"""

import streamlit as st
import streamlit_authenticator as stauth
import yaml
from datetime import date
from pathlib import Path

from data.store import get_dashboard_data, init_db
from ui_style import (
    inject_custom_css,
    branded_header,
    sidebar_branding,
    sidebar_trust_badges,
    metric_card,
    urgency_badge,
    status_badge,
    empty_state,
    login_hero,
    BRAND_PRIMARY,
    COLOR_CRITICAL,
    COLOR_WARNING,
    COLOR_SUCCESS,
    COLOR_INFO,
    COLOR_NEUTRAL,
)

st.set_page_config(
    page_title="Lumen ABA — Reauth Agent",
    page_icon="&#9672;",
    layout="wide",
    initial_sidebar_state="expanded",
)

inject_custom_css()

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
sidebar_trust_badges()

init_db()

branded_header("Dashboard", "Manage clients, track auth deadlines, and resume work-in-progress.")

# --- Dashboard ---
dashboard = get_dashboard_data()

if not dashboard:
    empty_state(
        "&#128203;",
        "No clients yet",
        "Add your first client to start managing reauthorizations.",
        "Go to Clients",
    )
    st.stop()

# Summary metrics as styled cards
total = len(dashboard)
critical = sum(1 for d in dashboard if d["urgency"] == "critical")
soon = sum(1 for d in dashboard if d["urgency"] == "soon")
expired = sum(1 for d in dashboard if d["urgency"] == "expired")
in_progress = sum(1 for d in dashboard if d.get("period_status") in ("in_progress", "generated"))

col1, col2, col3, col4, col5 = st.columns(5)
with col1:
    st.markdown(metric_card("Total Clients", total, BRAND_PRIMARY, "&#128101;"), unsafe_allow_html=True)
with col2:
    st.markdown(metric_card("Expired", expired, COLOR_CRITICAL, "&#9888;"), unsafe_allow_html=True)
with col3:
    st.markdown(metric_card("Due < 14 Days", critical, COLOR_CRITICAL, "&#128308;"), unsafe_allow_html=True)
with col4:
    st.markdown(metric_card("Due < 30 Days", soon, COLOR_WARNING, "&#128992;"), unsafe_allow_html=True)
with col5:
    st.markdown(metric_card("In Progress", in_progress, COLOR_SUCCESS, "&#9997;"), unsafe_allow_html=True)

st.markdown("<div style='height: 20px;'></div>", unsafe_allow_html=True)

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

STATUS_LABELS = {
    "draft": "Draft",
    "in_progress": "Reviewing",
    "generated": "Narrative Ready",
    "exported": "Exported",
    "submitted": "Submitted",
    None: "\u2014",
}

STATUS_COLORS = {
    "draft": COLOR_INFO,
    "in_progress": COLOR_WARNING,
    "generated": COLOR_SUCCESS,
    "exported": COLOR_SUCCESS,
    "submitted": COLOR_SUCCESS,
    None: COLOR_NEUTRAL,
}

# Client table
for d in filtered:
    badge_html = urgency_badge(d["urgency"])
    status_label = STATUS_LABELS.get(d.get("period_status"), "\u2014")
    status_color = STATUS_COLORS.get(d.get("period_status"), COLOR_NEUTRAL)
    dx = ", ".join(d["diagnosis_codes"][:2]) if d["diagnosis_codes"] else "\u2014"

    if d["period_end"]:
        days = d["days_until_expiry"]
        if days < 0:
            expiry_text = f"Expired {abs(days)}d ago"
        else:
            expiry_text = f"{days}d remaining"
    else:
        expiry_text = "No auth period"

    # Render as a card-style row
    st.markdown('<div class="client-row">', unsafe_allow_html=True)

    col_badge, col_name, col_dx, col_expiry, col_status, col_action = st.columns([1, 2.5, 1.5, 1.5, 1.5, 1.5])

    with col_badge:
        st.markdown(badge_html, unsafe_allow_html=True)
    with col_name:
        st.markdown(f"**{d['display_name']}**")
        if d["client_identifier"]:
            st.caption(d["client_identifier"])
    with col_dx:
        st.caption("Diagnosis")
        st.write(dx)
    with col_expiry:
        st.caption("Auth Expiry")
        st.write(expiry_text)
    with col_status:
        st.caption("Status")
        st.markdown(status_badge(status_label, status_color), unsafe_allow_html=True)
    with col_action:
        st.caption("Action")
        if d.get("period_id"):
            if st.button("Open", key=f"open_{d['client_id']}", use_container_width=True):
                st.session_state.selected_client_id = d["client_id"]
                st.session_state.selected_period_id = d["period_id"]
                st.switch_page("pages/2_Client_Detail.py")
        else:
            if st.button("Set Up", key=f"setup_{d['client_id']}", use_container_width=True):
                st.session_state.selected_client_id = d["client_id"]
                st.switch_page("pages/2_Client_Detail.py")

    st.markdown('</div>', unsafe_allow_html=True)
