"""Page 5: Generate reauthorization narrative with BCBA review.

Provides side-by-side view of source data and generated narrative for each section.
BCBAs can edit every narrative section directly. Edits persist to DB.
Shows prior period data for comparison when available.
"""

import json

import streamlit as st
from dotenv import load_dotenv

load_dotenv()

from data.store import get_auth_period, get_prior_period, save_narrative
from pipeline.generator import generate_narrative, validate_narrative_against_source
from schemas.narrative import AnthemReauthNarrative
from ui_style import (
    inject_custom_css,
    branded_header,
    sidebar_branding,
    sidebar_trust_badges,
    section_header,
    progress_bar_html,
    status_badge,
    metric_card,
    COLOR_SUCCESS,
    COLOR_WARNING,
    COLOR_CRITICAL,
    COLOR_INFO,
    BRAND_PRIMARY,
)

inject_custom_css()
sidebar_branding()
sidebar_trust_badges()

branded_header("Generate Reauthorization Narrative", "AI-generated draft for BCBA review and editing.")

# Load from DB
period_id = st.session_state.get("selected_period_id")
client_id = st.session_state.get("selected_client_id")

if period_id:
    period = get_auth_period(period_id)
    if period and period.get("extracted_data_parsed"):
        st.session_state.clinical_data = period["extracted_data_parsed"]
        if period.get("validation_result_parsed"):
            st.session_state.validation = period["validation_result_parsed"]
    if period and period.get("narrative_data_parsed"):
        st.session_state.narrative = period["narrative_data_parsed"]

if st.session_state.get("clinical_data") is None:
    st.warning("No data extracted yet. Go to **Upload** first.")
    st.stop()

data = st.session_state.clinical_data

# Prior period comparison
prior_period = None
if period_id and client_id:
    prior_period = get_prior_period(client_id, period_id)

if prior_period and prior_period.get("extracted_data_parsed"):
    st.markdown(
        '<div class="section-header">'
        '<span class="section-title">Progress Since Prior Authorization</span>'
        '</div>',
        unsafe_allow_html=True,
    )
    st.caption(f"Comparing against: {prior_period['period_start']} to {prior_period['period_end']}")

    prior_data = prior_period["extracted_data_parsed"]

    # Key deltas as metrics
    prior_mastered = sum(1 for t in prior_data.skill_acquisition_targets if t.is_mastered)
    current_mastered = sum(1 for t in data.skill_acquisition_targets if t.is_mastered)

    delta_col1, delta_col2, delta_col3 = st.columns(3)
    with delta_col1:
        st.metric(
            "Skills Mastered",
            current_mastered,
            delta=f"+{current_mastered - prior_mastered}" if current_mastered > prior_mastered else str(current_mastered - prior_mastered),
        )
    with delta_col2:
        st.metric("Current Skill Targets", len(data.skill_acquisition_targets))
    with delta_col3:
        st.metric("Current Behavior Targets", len(data.behavior_reduction_targets))

    # Behavior reduction comparison
    prior_behaviors = {b.behavior_name: b for b in prior_data.behavior_reduction_targets}
    behavior_changes = []
    for b in data.behavior_reduction_targets:
        prior_b = prior_behaviors.get(b.behavior_name)
        if prior_b and prior_b.current_value is not None and b.current_value is not None and prior_b.current_value > 0:
            pct_change = ((b.current_value - prior_b.current_value) / prior_b.current_value) * 100
            behavior_changes.append((b.behavior_name, prior_b.current_value, b.current_value, pct_change, b.unit))

    if behavior_changes:
        st.write("**Behavior Trends:**")
        for name, prior_val, curr_val, pct, unit in behavior_changes:
            direction = "decrease" if pct < 0 else "increase"
            st.write(f"- **{name}**: {prior_val} \u2192 {curr_val} {unit} ({abs(pct):.0f}% {direction})")

    st.divider()

# Check validation status
validation = st.session_state.get("validation", {})
if not validation.get("is_complete", False):
    st.markdown(
        '<div style="background:#FFFBEB; border:1px solid #FDE68A; border-radius:10px; padding:14px 18px;">'
        f'<strong style="color:#D97706;">Extracted data is incomplete</strong> (score: {validation.get("score", 0):.0%}). '
        'Narrative will contain placeholders for missing data.'
        '</div>',
        unsafe_allow_html=True,
    )

st.markdown("<div style='height:12px;'></div>", unsafe_allow_html=True)

if st.button("Generate Anthem Blue Cross Narrative", type="primary", use_container_width=True):
    with st.spinner("Generating narrative... (30-60 seconds)"):
        try:
            narrative = generate_narrative(data)
            st.session_state.narrative = narrative
            # Save to DB
            if period_id:
                save_narrative(period_id, narrative)

            confidence_color = COLOR_SUCCESS if narrative.overall_confidence >= 0.8 else COLOR_WARNING
            st.markdown(
                f'<div style="background:#ECFDF5; border:1px solid #A7F3D0; border-radius:10px; padding:14px 18px;">'
                f'<strong style="color:#059669;">Narrative generated successfully.</strong> '
                f'Confidence: '
                + progress_bar_html(narrative.overall_confidence * 100, 100, confidence_color)
                + '</div>',
                unsafe_allow_html=True,
            )
        except Exception as e:
            st.error(f"Generation failed: {e}")
            st.exception(e)
            st.stop()

    # Post-generation validation
    with st.spinner("Cross-validating against source data..."):
        discrepancies = validate_narrative_against_source(narrative, data)
        if discrepancies:
            st.warning(f"{len(discrepancies)} potential discrepancies found:")
            for d in discrepancies:
                st.write(d)
        else:
            st.success("No discrepancies detected in cross-validation.")

if st.session_state.get("narrative") is None:
    st.stop()

narrative = st.session_state.narrative

# Display narrative sections for BCBA review with side-by-side source data
st.markdown("---")
st.markdown(
    '<div class="section-header">'
    '<span class="section-title">BCBA Review \u2014 Edit Narrative Sections</span>'
    '</div>',
    unsafe_allow_html=True,
)

st.markdown(
    '<div style="background:#F0F7F9; padding:12px 16px; border-radius:8px; margin-bottom:16px; font-size:13px; color:#6B7280;">'
    '<strong style="color:#1A2B3C;">Left:</strong> source data for verification. '
    '<strong style="color:#1A2B3C;">Right:</strong> AI-generated draft \u2014 '
    '<strong>edit directly in the text boxes</strong>. Your clinical judgment takes precedence over AI output.'
    '</div>',
    unsafe_allow_html=True,
)

# Map sections to their relevant source data fields for side-by-side display
SECTION_SOURCE_MAP = {
    "client_overview": lambda d: {
        "client": d.client.model_dump(mode="json"),
    },
    "assessment_summary": lambda d: {
        "assessments": [a.model_dump(mode="json") for a in d.assessments],
    },
    "skill_acquisition_progress": lambda d: {
        "skill_acquisition_targets": [t.model_dump(mode="json") for t in d.skill_acquisition_targets],
    },
    "behavior_reduction_progress": lambda d: {
        "behavior_reduction_targets": [b.model_dump(mode="json") for b in d.behavior_reduction_targets],
    },
    "treatment_plan_update": lambda d: {
        "treatment_goals": [g.model_dump(mode="json") for g in d.treatment_goals],
    },
    "hours_justification": lambda d: {
        "hours_utilization": [h.model_dump(mode="json") for h in d.hours_utilization],
        "requested_hours_by_code": d.requested_hours_by_code,
        "clinical_justification_for_hours": d.clinical_justification_for_hours,
    },
    "caregiver_training_summary": lambda d: {
        "caregiver_training": d.caregiver_training.model_dump(mode="json"),
    },
    "medical_necessity": lambda d: {
        "client_diagnosis": d.client.diagnosis_codes,
        "assessments_summary": [
            {"name": a.assessment_name, "standard_score": a.standard_score, "percentile": a.percentile}
            for a in d.assessments
        ],
        "behavior_trends": [
            {"name": b.behavior_name, "trend": b.trend.value if b.trend else None, "baseline": b.baseline_value, "current": b.current_value}
            for b in d.behavior_reduction_targets
        ],
    },
    "discharge_plan": lambda d: {
        "discharge_plan": d.discharge_plan.model_dump(mode="json"),
    },
}

sections = [
    ("client_overview", "1. Client Overview"),
    ("assessment_summary", "2. Assessment Summary"),
    ("skill_acquisition_progress", "3. Skill Acquisition Progress"),
    ("behavior_reduction_progress", "4. Behavior Reduction Progress"),
    ("treatment_plan_update", "5. Treatment Plan Update"),
    ("hours_justification", "6. Hours Utilization & Justification"),
    ("caregiver_training_summary", "7. Caregiver Training"),
    ("medical_necessity", "8. Medical Necessity Statement"),
    ("discharge_plan", "9. Discharge Plan"),
]

for field_name, display_name in sections:
    section = getattr(narrative, field_name)
    flag_badge = status_badge("Needs Review", COLOR_WARNING) if section.requires_review else status_badge("OK", COLOR_SUCCESS)

    with st.expander(f"{display_name}", expanded=section.requires_review):
        st.markdown(flag_badge, unsafe_allow_html=True)

        if section.requires_review and section.review_note:
            st.warning(f"Review needed: {section.review_note}")

        # Side-by-side: source data (left) | narrative editor (right)
        col_source, col_narrative = st.columns(2)

        with col_source:
            st.markdown(
                '<p style="font-size:12px; font-weight:600; color:#6B7280; text-transform:uppercase; letter-spacing:0.5px;">'
                'Source Data (read-only reference)</p>',
                unsafe_allow_html=True,
            )
            source_fn = SECTION_SOURCE_MAP.get(field_name)
            if source_fn:
                source_data = source_fn(data)
                st.json(json.loads(json.dumps(source_data, default=str)))

        with col_narrative:
            st.markdown(
                '<p style="font-size:12px; font-weight:600; color:#6B7280; text-transform:uppercase; letter-spacing:0.5px;">'
                'Narrative (edit below)</p>',
                unsafe_allow_html=True,
            )
            edited = st.text_area(
                f"Edit {display_name}",
                value=section.content,
                height=250,
                key=f"edit_{field_name}",
                label_visibility="collapsed",
            )
            section.content = edited

            word_count = len(edited.split())
            if word_count < 50:
                st.markdown(
                    f'<span style="font-size:12px; color:{COLOR_WARNING};">'
                    f'{word_count} words \u2014 may be too brief for payor</span>',
                    unsafe_allow_html=True,
                )
            elif word_count > 400:
                st.markdown(
                    f'<span style="font-size:12px; color:{COLOR_WARNING};">'
                    f'{word_count} words \u2014 consider condensing</span>',
                    unsafe_allow_html=True,
                )
            else:
                st.caption(f"{word_count} words")

# Show flags
if narrative.flags_for_bcba:
    st.markdown("---")
    st.markdown(
        '<div class="section-header">'
        '<span class="section-title">Items Requiring BCBA Attention</span>'
        f'<span class="section-count">{len(narrative.flags_for_bcba)} flag{"s" if len(narrative.flags_for_bcba) != 1 else ""}</span>'
        '</div>',
        unsafe_allow_html=True,
    )
    for flag_text in narrative.flags_for_bcba:
        st.markdown(
            f'<div style="background:#FFFBEB; border-left:4px solid {COLOR_WARNING}; '
            f'padding:8px 14px; border-radius:0 8px 8px 0; margin-bottom:6px; font-size:14px;">'
            f'{flag_text}</div>',
            unsafe_allow_html=True,
        )

st.markdown("---")

# Save & continue
col1, col2 = st.columns([2, 1])
with col1:
    if st.button("Save All Edits", type="primary", use_container_width=True):
        st.session_state.narrative = narrative
        if period_id:
            save_narrative(period_id, narrative)
        st.toast("All narrative edits saved.", icon="\u2705")
        st.success("Edits saved. Navigate to **Export** to download as Word document.")

with col2:
    st.page_link("pages/6_Export.py", label="Continue to Export \u2192", use_container_width=True)
