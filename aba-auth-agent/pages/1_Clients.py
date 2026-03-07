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

st.header("Clients")

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

st.divider()

# --- Client List ---
clients = list_clients(status="active")

if not clients:
    st.info("No clients yet. Add your first client above.")
    st.stop()

for c in clients:
    col_name, col_id, col_dx, col_payor, col_actions = st.columns([2, 1.5, 1.5, 1.5, 2])

    with col_name:
        st.write(f"**{c['display_name']}**")
    with col_id:
        st.write(c.get("client_identifier") or "—")
    with col_dx:
        st.write(", ".join(c["diagnosis_codes"][:2]) if c["diagnosis_codes"] else "—")
    with col_payor:
        st.write(c["payor"].replace("_", " ").title()[:20])
    with col_actions:
        btn_col1, btn_col2, btn_col3 = st.columns(3)
        with btn_col1:
            if st.button("View", key=f"view_{c['id']}", use_container_width=True):
                st.session_state.selected_client_id = c["id"]
                st.switch_page("pages/2_Client_Detail.py")
        with btn_col2:
            if st.button("Upload", key=f"upload_{c['id']}", use_container_width=True):
                st.session_state.selected_client_id = c["id"]
                st.switch_page("pages/3_Upload.py")
        with btn_col3:
            confirm_key = f"confirm_archive_{c['id']}"
            if st.session_state.get(confirm_key):
                st.warning(f"Archive **{c['display_name']}**?")
                yes_col, no_col = st.columns(2)
                with yes_col:
                    if st.button("Yes, archive", key=f"yes_archive_{c['id']}", type="primary", use_container_width=True):
                        update_client(c["id"], status="discharged")
                        st.session_state.pop(confirm_key, None)
                        st.rerun()
                with no_col:
                    if st.button("Cancel", key=f"cancel_archive_{c['id']}", use_container_width=True):
                        st.session_state.pop(confirm_key, None)
                        st.rerun()
            else:
                if st.button("Archive", key=f"archive_{c['id']}", use_container_width=True):
                    st.session_state[confirm_key] = True
                    st.rerun()
