"""Page 1: Client Management — add, edit, and view clients."""

import streamlit as st

from data.store import (
    create_client,
    list_clients,
    update_client,
    delete_client,
    create_auth_period,
)
from pipeline.exporter import list_available_payors
from ui_style import (
    inject_custom_css,
    branded_header,
    sidebar_branding,
    sidebar_trust_badges,
    empty_state,
    status_badge,
    COLOR_SUCCESS,
    COLOR_NEUTRAL,
    BRAND_PRIMARY,
)

inject_custom_css()
sidebar_branding()
sidebar_trust_badges()

branded_header("Clients", "Manage your ABA client roster.")

# --- Add Client ---
with st.expander("+ Add New Client", expanded=False):
    with st.form("add_client"):
        col1, col2 = st.columns(2)
        with col1:
            name = st.text_input("Display Name (de-identified)", placeholder="Martinez, A.")
            identifier = st.text_input("Client ID (practice system)", placeholder="CR-2024-0847")
        with col2:
            dx = st.text_input("Diagnosis Codes (comma-separated)", placeholder="F84.0, F80.2")
            payor_options = list_available_payors()
            payor_keys = list(payor_options.keys())
            payor = st.selectbox(
                "Primary Payor",
                payor_keys,
                format_func=lambda k: payor_options[k]["display_name"],
            )

        submitted = st.form_submit_button("Add Client", type="primary")
        if submitted and name:
            dx_list = [c.strip() for c in dx.split(",") if c.strip()] if dx else []
            client_id = create_client(
                display_name=name,
                client_identifier=identifier or None,
                diagnosis_codes=dx_list,
                payor=payor,
            )
            st.success(f"Client '{name}' created.")
            st.rerun()
        elif submitted:
            st.error("Display name is required.")

st.markdown("<div style='height: 8px;'></div>", unsafe_allow_html=True)

# --- Client List ---
clients = list_clients(status="active")

if not clients:
    empty_state(
        "&#128101;",
        "No clients yet",
        "Add your first client using the form above to start managing reauthorizations.",
    )
    st.stop()

# --- Search & Count Row ---
search_col, count_col = st.columns([3, 1])
with search_col:
    search_query = st.text_input(
        "Search clients",
        placeholder="Search by name, ID, diagnosis, or payor\u2026",
        label_visibility="collapsed",
    )
with count_col:
    st.markdown(
        f'<div style="display:flex; align-items:center; justify-content:flex-end; height:100%; padding-top:8px;">'
        f'<span class="client-count">'
        f'<span class="count-num">{len(clients)}</span> active client{"s" if len(clients) != 1 else ""}'
        f'</span></div>',
        unsafe_allow_html=True,
    )

# Filter clients by search
if search_query:
    q = search_query.lower()
    clients = [
        c for c in clients
        if q in c["display_name"].lower()
        or q in (c.get("client_identifier") or "").lower()
        or q in " ".join(c.get("diagnosis_codes") or []).lower()
        or q in c.get("payor", "").lower()
    ]

if not clients and search_query:
    st.info(f'No clients match "{search_query}".')
    st.stop()

# --- Table Header (HTML) ---
st.markdown(
    '<div class="client-table-wrap">'
    '<div class="client-table-header">'
    '<div>Client</div>'
    '<div>Diagnosis</div>'
    '<div>Payor</div>'
    '<div style="text-align:right;">Actions</div>'
    '</div>'
    '</div>',
    unsafe_allow_html=True,
)

# --- Client Rows ---
for c in clients:
    client_name = c["display_name"]
    client_id_str = c.get("client_identifier") or "\u2014"
    dx_str = ", ".join(c["diagnosis_codes"][:3]) if c["diagnosis_codes"] else "\u2014"
    payor_display = c["payor"].replace("_", " ").title()

    # Row HTML info
    st.markdown(
        '<div class="client-table-wrap" style="border-top:none; border-radius:0; margin-top:-1px;">',
        unsafe_allow_html=True,
    )

    row_cols = st.columns([2, 1.2, 1.5, 2])

    with row_cols[0]:
        st.markdown(
            f'<div class="client-name">{client_name}'
            f'<span class="client-id-sub">{client_id_str}</span></div>',
            unsafe_allow_html=True,
        )

    with row_cols[1]:
        if dx_str == "\u2014":
            st.markdown(f'<div class="client-cell-muted">{dx_str}</div>', unsafe_allow_html=True)
        else:
            st.markdown(f'<div class="client-cell">{dx_str}</div>', unsafe_allow_html=True)

    with row_cols[2]:
        st.markdown(
            f'<div><span class="client-payor-badge">{payor_display}</span></div>',
            unsafe_allow_html=True,
        )

    with row_cols[3]:
        btn_c1, btn_c2, btn_c3 = st.columns(3)
        with btn_c1:
            if st.button("View", key=f"view_{c['id']}", use_container_width=True, type="primary"):
                st.session_state.selected_client_id = c["id"]
                st.switch_page("pages/2_Client_Detail.py")
        with btn_c2:
            if st.button("Upload", key=f"upload_{c['id']}", use_container_width=True):
                st.session_state.selected_client_id = c["id"]
                st.switch_page("pages/3_Upload.py")
        with btn_c3:
            confirm_key = f"confirm_archive_{c['id']}"
            if st.session_state.get(confirm_key):
                st.warning(f"Archive **{c['display_name']}**?")
                yes_col, no_col = st.columns(2)
                with yes_col:
                    if st.button("Yes", key=f"yes_archive_{c['id']}", type="primary", use_container_width=True):
                        update_client(c["id"], status="discharged")
                        st.session_state.pop(confirm_key, None)
                        st.rerun()
                with no_col:
                    if st.button("Cancel", key=f"cancel_archive_{c['id']}", use_container_width=True):
                        st.session_state.pop(confirm_key, None)
                        st.rerun()
            else:
                if st.button("Archive", key=f"archive_{c['id']}", use_container_width=True, type="secondary"):
                    st.session_state[confirm_key] = True
                    st.rerun()

    st.markdown('</div>', unsafe_allow_html=True)
