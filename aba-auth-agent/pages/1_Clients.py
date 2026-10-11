"""Page 1: Client Management — add, edit, and view clients."""

import html

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
    with st.form("add_client", clear_on_submit=True):
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
payor_names = {k: v["display_name"] for k, v in list_available_payors().items()}
search_col, count_col = st.columns([3, 1], vertical_alignment="center")
search_query = search_col.text_input(
    "Search clients",
    placeholder="Search by name, ID, diagnosis, or payor\u2026",
    label_visibility="collapsed",
)

total_clients = len(clients)
if search_query:
    q = search_query.lower()
    clients = [
        c for c in clients
        if q in c["display_name"].lower()
        or q in (c.get("client_identifier") or "").lower()
        or q in " ".join(c.get("diagnosis_codes") or []).lower()
        or q in payor_names.get(c["payor"], c["payor"]).lower()
    ]

count_label = (
    f"of {total_clients} active clients" if search_query
    else f'active client{"s" if total_clients != 1 else ""}'
)
count_col.markdown(
    f'<div style="display:flex; justify-content:flex-end;"><span class="client-count">'
    f'<span class="count-num">{len(clients)}</span> {count_label}</span></div>',
    unsafe_allow_html=True,
)

if not clients and search_query:
    st.info(f'No clients match "{search_query}".')
    st.stop()

# --- Client Table ---
COL_WIDTHS = [2, 1.2, 1.8, 3]

with st.container(border=True):
    header = st.columns(COL_WIDTHS, vertical_alignment="center")
    for col, label in zip(header, ["Client", "Diagnosis", "Payor", "Actions"]):
        col.markdown(f'<div class="client-table-header-cell">{label}</div>', unsafe_allow_html=True)

    for c in clients:
        st.markdown('<hr class="client-table-divider">', unsafe_allow_html=True)

        name_html = html.escape(c["display_name"])
        id_html = html.escape(c.get("client_identifier") or "No client ID")
        dx_codes = c.get("diagnosis_codes") or []
        payor_display = payor_names.get(c["payor"], c["payor"].replace("_", " ").title())

        row = st.columns(COL_WIDTHS, vertical_alignment="center")
        row[0].markdown(
            f'<div class="client-name">{name_html}'
            f'<span class="client-id-sub">{id_html}</span></div>',
            unsafe_allow_html=True,
        )
        row[1].markdown(
            f'<div class="client-cell">{html.escape(", ".join(dx_codes))}</div>'
            if dx_codes else '<div class="client-cell-muted">\u2014</div>',
            unsafe_allow_html=True,
        )
        row[2].markdown(
            f'<div><span class="client-payor-badge" title="{html.escape(payor_display)}">'
            f'{html.escape(payor_display)}</span></div>',
            unsafe_allow_html=True,
        )

        confirm_key = f"confirm_archive_{c['id']}"
        with row[3]:
            b1, b2, b3 = st.columns(3, gap="small")
            if b1.button("View", key=f"view_{c['id']}", use_container_width=True, type="primary"):
                st.session_state.selected_client_id = c["id"]
                st.switch_page("pages/2_Client_Detail.py")
            if b2.button("Upload", key=f"upload_{c['id']}", use_container_width=True):
                st.session_state.selected_client_id = c["id"]
                st.switch_page("pages/3_Upload.py")
            if b3.button("Archive", key=f"archive_{c['id']}", use_container_width=True,
                         disabled=bool(st.session_state.get(confirm_key))):
                st.session_state[confirm_key] = True
                st.rerun()

        if st.session_state.get(confirm_key):
            msg_col, yes_col, no_col = st.columns([5, 1.2, 1.2], vertical_alignment="center")
            msg_col.warning(f"Archive **{c['display_name']}**? They'll be removed from the active roster.")
            if yes_col.button("Yes, archive", key=f"yes_archive_{c['id']}", type="primary", use_container_width=True):
                update_client(c["id"], status="discharged")
                st.session_state.pop(confirm_key, None)
                st.rerun()
            if no_col.button("Cancel", key=f"cancel_archive_{c['id']}", use_container_width=True):
                st.session_state.pop(confirm_key, None)
                st.rerun()
