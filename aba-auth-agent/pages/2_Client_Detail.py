"""Page 2: Client Detail — auth period history, assessment trends, resume work."""

import streamlit as st
from datetime import date, timedelta

from data.store import (
    get_client,
    list_auth_periods,
    create_auth_period,
    update_period_notes,
)
from ui_style import (
    inject_custom_css,
    branded_header,
    sidebar_branding,
    sidebar_trust_badges,
    status_badge,
    metric_card,
    progress_bar_html,
    empty_state,
    COLOR_CRITICAL,
    COLOR_WARNING,
    COLOR_SUCCESS,
    COLOR_INFO,
    COLOR_NEUTRAL,
    BRAND_PRIMARY,
)

inject_custom_css()
sidebar_branding()
sidebar_trust_badges()

client_id = st.session_state.get("selected_client_id")
if not client_id:
    st.warning("No client selected. Go to **Clients** or the **Dashboard** first.")
    st.stop()

client = get_client(client_id)
if not client:
    st.error("Client not found.")
    st.stop()

# --- Client header ---
branded_header(
    client["display_name"],
    f"ID: {client.get('client_identifier') or '\u2014'}",
)

col1, col2, col3 = st.columns(3)
with col1:
    dx_text = ", ".join(client["diagnosis_codes"]) if client["diagnosis_codes"] else "\u2014"
    st.markdown(
        metric_card("Diagnosis", dx_text, BRAND_PRIMARY),
        unsafe_allow_html=True,
    )
with col2:
    st.markdown(
        metric_card("Payor", client["payor"].replace("_", " ").title(), COLOR_INFO),
        unsafe_allow_html=True,
    )
with col3:
    st.markdown(
        metric_card("Status", client.get("status", "active").title(), COLOR_SUCCESS),
        unsafe_allow_html=True,
    )

st.markdown("<div style='height:16px;'></div>", unsafe_allow_html=True)

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
    empty_state(
        "&#128197;",
        "No authorization periods",
        "Create your first auth period above to start tracking reauthorizations.",
    )
    st.stop()

STATUS_CONFIG = {
    "draft": ("Draft", COLOR_INFO),
    "in_progress": ("Reviewing", COLOR_WARNING),
    "generated": ("Narrative Ready", COLOR_SUCCESS),
    "exported": ("Exported", COLOR_SUCCESS),
    "submitted": ("Submitted", COLOR_SUCCESS),
}

st.markdown(
    f'<div class="section-header">'
    f'<span class="section-title">Authorization Periods</span>'
    f'<span class="section-count">{len(periods)} period{"s" if len(periods) != 1 else ""}</span>'
    f'</div>',
    unsafe_allow_html=True,
)

for p in periods:
    badge_text, badge_color = STATUS_CONFIG.get(p["status"], ("Unknown", COLOR_NEUTRAL))
    badge_html = status_badge(badge_text, badge_color)
    title = f"{p['period_start']} to {p['period_end']}"

    with st.expander(f"{title} \u2014 {badge_text}", expanded=(p["id"] == st.session_state.get("selected_period_id"))):
        # Status badge at top
        st.markdown(badge_html, unsafe_allow_html=True)
        st.markdown("<div style='height:8px;'></div>", unsafe_allow_html=True)

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
                st.metric("Extracted", "\u2014")
        with col4:
            if p.get("exported_at"):
                st.metric("Exported", p["exported_at"][:10])
            else:
                st.metric("Exported", "\u2014")

        # Validation summary (if exists)
        if p.get("validation_result_parsed"):
            vr = p["validation_result_parsed"]
            completeness_color = COLOR_SUCCESS if vr["score"] >= 0.8 else COLOR_WARNING
            st.markdown(
                f'<div style="margin:8px 0;">'
                f'<strong>Completeness:</strong> '
                + progress_bar_html(vr["score"] * 100, 100, completeness_color)
                + f' | <strong>Missing:</strong> {len(vr["missing"])} '
                f'| <strong>Warnings:</strong> {len(vr["warnings"])}'
                f'</div>',
                unsafe_allow_html=True,
            )

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
            confidence_color = COLOR_SUCCESS if nd.overall_confidence >= 0.8 else COLOR_WARNING
            st.markdown(
                f'<div style="margin:8px 0;">'
                f'<strong>Narrative Confidence:</strong> '
                + progress_bar_html(nd.overall_confidence * 100, 100, confidence_color)
                + f' | <strong>BCBA Flags:</strong> {len(nd.flags_for_bcba)}'
                f'</div>',
                unsafe_allow_html=True,
            )

        # Notes
        notes = st.text_area(
            "BCBA Notes",
            value=p.get("notes") or "",
            key=f"notes_{p['id']}",
            height=68,
        )
        if notes != (p.get("notes") or ""):
            update_period_notes(p["id"], notes)

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
    st.markdown(
        '<div class="section-header">'
        '<span class="section-title">Assessment Trends Across Periods</span>'
        '</div>',
        unsafe_allow_html=True,
    )

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
            row = [domain] + [str(d["scores"].get(domain, "\u2014")) for d in vbmapp_data]
            rows.append(row)

        import pandas as pd
        df = pd.DataFrame(rows, columns=header)
        st.dataframe(df, use_container_width=True, hide_index=True)
    else:
        st.caption("Need VB-MAPP data in 2+ periods to show trends.")
