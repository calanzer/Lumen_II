"""Page 1: Client Management — add, edit, and view clients."""

import pandas as pd
import streamlit as st
from st_aggrid import AgGrid, GridOptionsBuilder, StAggridTheme

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
    empty_state,
    status_badge,
    COLOR_SUCCESS,
    COLOR_NEUTRAL,
    BRAND_PRIMARY,
)

inject_custom_css()

branded_header("Clients", "Manage your ABA client roster.")

# --- Add Client (modal) ---
@st.dialog("Add client")
def add_client_dialog():
    payor_options = list_available_payors()
    with st.form("add_client", border=False):
        name = st.text_input("Name", placeholder="Martinez, A.")
        identifier = st.text_input("Client ID", placeholder="CR-2024-0847")
        dx = st.text_input("Diagnosis codes", placeholder="F84.0, F80.2")
        payor = st.selectbox(
            "Payor",
            list(payor_options.keys()),
            format_func=lambda k: payor_options[k]["display_name"],
        )
        submitted = st.form_submit_button("Add client", type="primary", width="stretch")

    if submitted:
        if not name.strip():
            st.error("Name is required.")
            return
        dx_list = [c.strip() for c in dx.split(",") if c.strip()]
        create_client(
            display_name=name.strip(),
            client_identifier=identifier.strip() or None,
            diagnosis_codes=dx_list,
            payor=payor,
        )
        st.rerun()  # closes the dialog and refreshes the table


# --- Client List ---
clients = list_clients(status="active")

if not clients:
    if st.button("Add client", type="primary"):
        add_client_dialog()
    empty_state(
        "&#128101;",
        "No clients yet",
        "Click Add client to start managing reauthorizations.",
    )
    st.stop()

# --- Search, Count & Add Row ---
# A horizontal container sizes children by role (search fills the free space, the
# button and count keep their natural width) and wraps on narrow screens, instead of
# splitting the row into fixed column ratios.
payor_names = {k: v["display_name"] for k, v in list_available_payors().items()}
total_clients = len(clients)

toolbar = st.container(horizontal=True, vertical_alignment="center")
search_query = toolbar.text_input(
    "Search clients",
    placeholder="Search by name, ID, diagnosis, or payor\u2026",
    label_visibility="collapsed",
    width="stretch",
)

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
toolbar.markdown(
    f'<span class="client-count"><span class="count-num">{len(clients)}</span> {count_label}</span>',
    unsafe_allow_html=True,
    width="content",
)
if toolbar.button("Add client", type="primary", width="content"):
    add_client_dialog()

if not clients and search_query:
    st.info(f'No clients match "{search_query}".')
    st.stop()

# --- Client Table ---
# Styled to match Streamlit's own table: light header, soft borders, brand-teal accents.
GRID_THEME = StAggridTheme(base="quartz").withParams(
    fontFamily='"Source Sans", "Source Sans Pro", -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif',
    fontSize=14,
    foregroundColor="#1A2B3C",
    backgroundColor="#FFFFFF",
    headerBackgroundColor="#F8FAFB",
    headerTextColor="#6B7280",
    headerFontWeight=400,
    borderColor="#E5E7EB",
    wrapperBorderRadius=8,
    rowHoverColor="#F0F7F9",
    selectedRowBackgroundColor="#E6F4F7",
    accentColor="#0B7285",
    rowHeight=40,
    headerHeight=40,
)

# AgGrid handles sorting, scrolling and row events. Single click selects a row and
# reveals its actions below; double click opens the client's details directly.
table = pd.DataFrame(
    {
        "id": [c["id"] for c in clients],
        "Client": [c["display_name"] for c in clients],
        "Client ID": [c.get("client_identifier") or "" for c in clients],
        "Diagnosis": [", ".join(c.get("diagnosis_codes") or []) for c in clients],
        "Payor": [payor_names.get(c["payor"], c["payor"].replace("_", " ").title()) for c in clients],
    }
)

grid_options = GridOptionsBuilder.from_dataframe(table)
grid_options.configure_column("id", hide=True)
grid_options.configure_column("Client", flex=2, minWidth=150, checkboxSelection=True)
grid_options.configure_column("Client ID", flex=1, minWidth=100)
grid_options.configure_column("Diagnosis", flex=1, minWidth=100)
grid_options.configure_column("Payor", flex=2, minWidth=210)
grid_options.configure_selection("single")
grid_options.configure_grid_options(suppressCellFocus=True)

grid = AgGrid(
    table,
    gridOptions=grid_options.build(),
    update_on=["selectionChanged", "rowDoubleClicked"],
    data_return_mode="AS_INPUT",
    height=min(44 + 40 * len(table), 520),
    theme=GRID_THEME,
    key="clients_grid",
)

by_id = {c["id"]: c for c in clients}

event = grid.event_data or {}
if event.get("type") == "rowDoubleClicked":
    dbl = event.get("data") or {}
    if dbl.get("id") in by_id:
        st.session_state.selected_client_id = dbl["id"]
        st.switch_page("pages/2_Client_Detail.py")

selected = grid.selected_rows
if selected is None or len(selected) == 0:
    st.caption("Click a client to select it. Double-click to open their details.")
    st.stop()

c = by_id[selected.iloc[0]["id"]]
confirm_key = f"confirm_archive_{c['id']}"

with st.container(border=True):
    st.markdown(f"**{c['display_name']}**")
    with st.container(horizontal=True):
        if st.button("View", key=f"view_{c['id']}", type="primary"):
            st.session_state.selected_client_id = c["id"]
            st.switch_page("pages/2_Client_Detail.py")
        if st.button("Upload report", key=f"upload_{c['id']}"):
            st.session_state.selected_client_id = c["id"]
            st.switch_page("pages/3_Upload.py")
        if st.button("Archive", key=f"archive_{c['id']}", disabled=bool(st.session_state.get(confirm_key))):
            st.session_state[confirm_key] = True
            st.rerun()

    if st.session_state.get(confirm_key):
        st.warning(f"Archive **{c['display_name']}**? They'll be removed from the active roster.")
        with st.container(horizontal=True):
            if st.button("Yes, archive", key=f"yes_archive_{c['id']}", type="primary"):
                update_client(c["id"], status="discharged")
                st.session_state.pop(confirm_key, None)
                st.rerun()
            if st.button("Cancel", key=f"cancel_archive_{c['id']}"):
                st.session_state.pop(confirm_key, None)
                st.rerun()
