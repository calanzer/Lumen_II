"""Page 2: Client Detail — auth period history, assessment trends, resume work."""

import streamlit as st
from datetime import date, timedelta

from data.store import (
    get_client,
    list_auth_periods,
    create_auth_period,
    update_period_notes,
)

st.header("Client Detail")

client_id = st.session_state.get("selected_client_id")
if not client_id:
    st.warning("No client selected. Go to **Clients** or the **Dashboard** first.")
    st.stop()

client = get_client(client_id)
if not client:
    st.error("Client not found.")
    st.stop()

# --- Client header ---
col1, col2, col3 = st.columns([2, 1, 1])
with col1:
    st.subheader(client["display_name"])
    if client.get("client_identifier"):
        st.caption(f"ID: {client['client_identifier']}")
with col2:
    st.write(f"**Dx:** {', '.join(client['diagnosis_codes']) if client['diagnosis_codes'] else '—'}")
with col3:
    st.write(f"**Payor:** {client['payor'].replace('_', ' ').title()}")

st.divider()

# --- New auth period ---
with st.expander("+ New Authorization Period", expanded=False):
    with st.form("new_period"):
        col1, col2 = st.columns(2)
        with col1:
            start = st.date_input("Period Start", value=date.today())
        with col2:
            end = st.date_input("Period End", value=date.today() + timedelta(days=182))

        if st.form_submit_button("Create Period", type="primary"):
            period_id = create_auth_period(client_id, start.isoformat(), end.isoformat())
            st.session_state.selected_period_id = period_id
            st.success("Auth period created. Upload a progress report to begin.")
            st.rerun()

# --- Auth period history ---
periods = list_auth_periods(client_id)

if not periods:
    st.info("No authorization periods yet. Create one above to get started.")
    st.stop()

STATUS_BADGES = {
    "draft": ("Draft", "🔵"),
    "in_progress": ("Reviewing", "🟡"),
    "generated": ("Narrative Ready", "🟢"),
    "exported": ("Exported", "✅"),
    "submitted": ("Submitted", "✅"),
}

st.subheader(f"Authorization Periods ({len(periods)})")

for p in periods:
    badge_text, badge_icon = STATUS_BADGES.get(p["status"], ("Unknown", "⚪"))
    title = f"{badge_icon} {p['period_start']} to {p['period_end']} — {badge_text}"

    with st.expander(title, expanded=(p["id"] == st.session_state.get("selected_period_id"))):
        # Status and dates
        col1, col2, col3, col4 = st.columns(4)
        with col1:
            st.metric("Status", badge_text)
        with col2:
            if p.get("uploaded_filename"):
                st.metric("Source", p["uploaded_filename"][:25])
            else:
                st.metric("Source", "Not uploaded")
        with col3:
            if p.get("extracted_at"):
                st.metric("Extracted", p["extracted_at"][:10])
            else:
                st.metric("Extracted", "—")
        with col4:
            if p.get("exported_at"):
                st.metric("Exported", p["exported_at"][:10])
            else:
                st.metric("Exported", "—")

        # Validation summary (if exists)
        if p.get("validation_result_parsed"):
            vr = p["validation_result_parsed"]
            st.write(f"**Completeness:** {vr['score']:.0%} | **Missing:** {len(vr['missing'])} | **Warnings:** {len(vr['warnings'])}")

        # Quick data summary (if extraction exists)
        if p.get("extracted_data_parsed"):
            ed = p["extracted_data_parsed"]
            cols = st.columns(5)
            cols[0].write(f"**Assessments:** {len(ed.assessments)}")
            cols[1].write(f"**Skill Targets:** {len(ed.skill_acquisition_targets)}")
            cols[2].write(f"**Behaviors:** {len(ed.behavior_reduction_targets)}")
            cols[3].write(f"**Goals:** {len(ed.treatment_goals)}")
            cols[4].write(f"**Hours Codes:** {len(ed.hours_utilization)}")

        # Narrative confidence (if generated)
        if p.get("narrative_data_parsed"):
            nd = p["narrative_data_parsed"]
            st.write(f"**Narrative Confidence:** {nd.overall_confidence:.0%} | **BCBA Flags:** {len(nd.flags_for_bcba)}")

        # Notes
        notes = st.text_area(
            "BCBA Notes",
            value=p.get("notes") or "",
            key=f"notes_{p['id']}",
            height=68,
        )
        if notes != (p.get("notes") or ""):
            if st.button("Save Notes", key=f"save_notes_{p['id']}", type="secondary"):
                update_period_notes(p["id"], notes)
                st.toast("Notes saved.", icon="✅")
                st.rerun()

        # Action buttons
        st.divider()
        btn_cols = st.columns(4)

        with btn_cols[0]:
            if p["status"] == "draft" or not p.get("extracted_data"):
                if st.button("Upload Report", key=f"upload_{p['id']}", use_container_width=True, type="primary"):
                    st.session_state.selected_client_id = client_id
                    st.session_state.selected_period_id = p["id"]
                    st.switch_page("pages/3_Upload.py")

        with btn_cols[1]:
            if p.get("extracted_data"):
                if st.button("Review Data", key=f"review_{p['id']}", use_container_width=True):
                    st.session_state.selected_client_id = client_id
                    st.session_state.selected_period_id = p["id"]
                    st.switch_page("pages/4_Review_Data.py")

        with btn_cols[2]:
            if p.get("extracted_data"):
                if st.button("Generate", key=f"gen_{p['id']}", use_container_width=True):
                    st.session_state.selected_client_id = client_id
                    st.session_state.selected_period_id = p["id"]
                    st.switch_page("pages/5_Generate.py")

        with btn_cols[3]:
            if p.get("narrative_data"):
                if st.button("Export", key=f"export_{p['id']}", use_container_width=True):
                    st.session_state.selected_client_id = client_id
                    st.session_state.selected_period_id = p["id"]
                    st.switch_page("pages/6_Export.py")

# --- Assessment trend comparison ---
periods_with_data = [p for p in periods if p.get("extracted_data_parsed")]
if len(periods_with_data) >= 2:
    st.divider()
    st.subheader("Assessment Trends Across Periods")

    # Collect VB-MAPP scores across periods
    vbmapp_data = []
    for p in reversed(periods_with_data):  # chronological order
        ed = p["extracted_data_parsed"]
        for a in ed.assessments:
            if a.assessment_type.value == "VB-MAPP" and a.domain_scores:
                vbmapp_data.append({
                    "period": f"{p['period_start'][:7]}",
                    "scores": a.domain_scores,
                })

    if len(vbmapp_data) >= 2:
        st.write("**VB-MAPP Domain Scores Over Time:**")
        # Show as a simple comparison table
        domains = list(vbmapp_data[0]["scores"].keys())
        header = ["Domain"] + [d["period"] for d in vbmapp_data]
        rows = []
        for domain in domains[:10]:  # Top 10 domains
            row = [domain] + [str(d["scores"].get(domain, "—")) for d in vbmapp_data]
            rows.append(row)

        import pandas as pd
        df = pd.DataFrame(rows, columns=header)
        st.dataframe(df, use_container_width=True, hide_index=True)
    else:
        st.caption("Need VB-MAPP data in 2+ periods to show trends.")
