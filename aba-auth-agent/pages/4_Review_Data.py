"""Page 4: Review and edit extracted clinical data.

BCBAs can edit every field inline before generating the narrative.
Changes are saved to both session state and the database.
"""

import json
from datetime import date, datetime

import streamlit as st

from data.store import get_auth_period, save_clinical_data
from schemas.clinical_data import (
    AssessmentType,
    BehaviorTrend,
    CPTCode,
    ExtractedClinicalData,
)
from ui_style import (
    inject_custom_css,
    branded_header,
    sidebar_branding,
    sidebar_trust_badges,
    section_header,
    progress_bar_html,
    status_badge,
    COLOR_SUCCESS,
    COLOR_WARNING,
    COLOR_CRITICAL,
    BRAND_PRIMARY,
)

inject_custom_css()
sidebar_branding()
sidebar_trust_badges()

branded_header("Review & Edit Extracted Data", "Verify clinical data before generating the reauthorization narrative.")

# Load from DB only when switching periods — not on every rerun
period_id = st.session_state.get("selected_period_id")
_loaded_period = st.session_state.get("_review_loaded_period_id")

if period_id and period_id != _loaded_period:
    period = get_auth_period(period_id)
    if period and period.get("extracted_data_parsed"):
        st.session_state.clinical_data = period["extracted_data_parsed"]
        if period.get("validation_result_parsed"):
            st.session_state.validation = period["validation_result_parsed"]
    st.session_state._review_loaded_period_id = period_id

if st.session_state.get("clinical_data") is None:
    st.warning("No data extracted yet. Go to **Upload** first.")
    st.stop()

data: ExtractedClinicalData = st.session_state.clinical_data

# Top save bar — always visible
_top_save_col1, _top_save_col2 = st.columns([3, 1])
with _top_save_col2:
    _top_save = st.button("Save All Changes", type="primary", use_container_width=True, key="save_top")


def _date_to_value(d):
    """Convert date/None to a date object for date_input."""
    if d is None:
        return None
    if isinstance(d, date):
        return d
    return datetime.strptime(str(d), "%Y-%m-%d").date()


def _save_all():
    """Rebuild, re-validate, save to session + DB."""
    try:
        dumped = data.model_dump(mode="json")
        updated = ExtractedClinicalData.model_validate(dumped)
        st.session_state.clinical_data = updated
        # Re-run validation
        from pipeline.validator import validate_completeness
        validation = validate_completeness(updated)
        st.session_state.validation = validation
        # Persist to database
        if period_id:
            save_clinical_data(period_id, updated, validation)
        st.toast("All changes saved.", icon="\u2705")
    except Exception as e:
        st.error(f"Validation error: {e}")


# --- Validation summary banner ---
validation = st.session_state.get("validation")
if validation:
    completeness_color = COLOR_SUCCESS if validation["score"] >= 0.8 else COLOR_WARNING
    if validation["is_complete"]:
        st.markdown(
            '<div style="background:#ECFDF5; border:1px solid #A7F3D0; border-radius:10px; padding:14px 18px; margin-bottom:16px;">'
            f'<strong style="color:#059669;">Data completeness: {validation["score"]:.0%}</strong> '
            '\u2014 all required fields found. '
            + progress_bar_html(validation["score"] * 100, 100, COLOR_SUCCESS)
            + '</div>',
            unsafe_allow_html=True,
        )
    else:
        st.markdown(
            '<div style="background:#FFFBEB; border:1px solid #FDE68A; border-radius:10px; padding:14px 18px; margin-bottom:16px;">'
            f'<strong style="color:#D97706;">Data completeness: {validation["score"]:.0%}</strong> '
            f'\u2014 {len(validation["missing"])} required fields missing. Edit below to fix. '
            + progress_bar_html(validation["score"] * 100, 100, COLOR_WARNING)
            + '</div>',
            unsafe_allow_html=True,
        )
    if validation.get("warnings"):
        with st.expander(f"{len(validation['warnings'])} warnings", expanded=False):
            for w in validation["warnings"]:
                st.write(f"- {w}")


# ===================================================================
# 1. Client Demographics
# ===================================================================
section_header(1, "Client Demographics")

col1, col2 = st.columns(2)
with col1:
    data.client.client_id = st.text_input(
        "Client ID", value=data.client.client_id or "", key="client_id"
    )
    data.client.age_years = st.number_input(
        "Age (years)", min_value=0, max_value=99,
        value=data.client.age_years or 0, key="age_years"
    )
    data.client.supervising_bcba = st.text_input(
        "Supervising BCBA", value=data.client.supervising_bcba or "", key="bcba_name"
    )
    data.client.bcba_credential_number = st.text_input(
        "BCBA Credential #", value=data.client.bcba_credential_number or "", key="bcba_cred"
    )

with col2:
    dx_codes_str = st.text_input(
        "Diagnosis Codes (comma-separated)",
        value=", ".join(data.client.diagnosis_codes),
        key="dx_codes",
    )
    data.client.diagnosis_codes = [c.strip() for c in dx_codes_str.split(",") if c.strip()]

    dx_desc_str = st.text_area(
        "Diagnosis Descriptions (one per line)",
        value="\n".join(data.client.diagnosis_descriptions),
        height=68, key="dx_desc",
    )
    data.client.diagnosis_descriptions = [d.strip() for d in dx_desc_str.split("\n") if d.strip()]

    col_a, col_b = st.columns(2)
    with col_a:
        data.client.auth_period_start = st.date_input(
            "Auth Period Start",
            value=_date_to_value(data.client.auth_period_start),
            key="auth_start",
        )
    with col_b:
        data.client.auth_period_end = st.date_input(
            "Auth Period End",
            value=_date_to_value(data.client.auth_period_end),
            key="auth_end",
        )

st.divider()

# ===================================================================
# 2. Assessments
# ===================================================================
section_header(2, "Assessments", f"{len(data.assessments)} found")

for i, a in enumerate(data.assessments):
    with st.expander(f"{a.assessment_type.value}: {a.assessment_name}", expanded=False):
        col1, col2, col3 = st.columns(3)
        with col1:
            type_options = [t.value for t in AssessmentType]
            current_idx = type_options.index(a.assessment_type.value) if a.assessment_type.value in type_options else 0
            new_type = st.selectbox("Type", type_options, index=current_idx, key=f"assess_type_{i}")
            a.assessment_type = AssessmentType(new_type)
        with col2:
            a.assessment_name = st.text_input("Name", value=a.assessment_name, key=f"assess_name_{i}")
        with col3:
            a.date_administered = st.date_input(
                "Date Administered", value=_date_to_value(a.date_administered), key=f"assess_date_{i}",
            )

        col1, col2, col3, col4 = st.columns(4)
        with col1:
            raw_str = st.text_input(
                "Raw Score", value=str(a.raw_score) if a.raw_score is not None else "",
                placeholder="Not assessed", key=f"assess_raw_{i}",
            )
            a.raw_score = float(raw_str) if raw_str.strip() else None
        with col2:
            std_str = st.text_input(
                "Standard Score", value=str(a.standard_score) if a.standard_score is not None else "",
                placeholder="Not assessed", key=f"assess_std_{i}",
            )
            a.standard_score = float(std_str) if std_str.strip() else None
        with col3:
            pct_str = st.text_input(
                "Percentile", value=str(a.percentile) if a.percentile is not None else "",
                placeholder="Not assessed", key=f"assess_pct_{i}",
            )
            a.percentile = float(pct_str) if pct_str.strip() else None
        with col4:
            val = st.text_input("Age Equivalent", value=a.age_equivalent or "", key=f"assess_age_eq_{i}")
            a.age_equivalent = val or None

        # Domain scores
        if a.domain_scores:
            st.write("**Domain Scores:**")
            domain_items = list(a.domain_scores.items())
            cols = st.columns(min(4, len(domain_items)))
            for j, (domain, score) in enumerate(domain_items):
                with cols[j % len(cols)]:
                    a.domain_scores[domain] = st.number_input(
                        domain, value=float(score), format="%.1f", key=f"assess_domain_{i}_{j}",
                    )

        col1, col2 = st.columns(2)
        with col1:
            prev_str = st.text_input(
                "Previous Score", value=str(a.previous_score) if a.previous_score is not None else "",
                placeholder="Not assessed", key=f"assess_prev_{i}",
            )
            a.previous_score = float(prev_str) if prev_str.strip() else None
        with col2:
            a.previous_date = st.date_input(
                "Previous Date", value=_date_to_value(a.previous_date), key=f"assess_prev_date_{i}",
            )

        if st.button("Remove this assessment", key=f"rm_assess_{i}", type="secondary"):
            data.assessments.pop(i)
            st.rerun()

if st.button("+ Add Assessment", key="add_assessment"):
    from schemas.clinical_data import StandardizedAssessment
    data.assessments.append(StandardizedAssessment(
        assessment_type=AssessmentType.OTHER,
        assessment_name="New Assessment",
        date_administered=date.today(),
    ))
    st.rerun()

st.divider()

# ===================================================================
# 3. Skill Acquisition Targets
# ===================================================================
mastered = sum(1 for t in data.skill_acquisition_targets if t.is_mastered)
section_header(3, "Skill Acquisition Targets", f"{mastered}/{len(data.skill_acquisition_targets)} mastered")

for i, t in enumerate(data.skill_acquisition_targets):
    mastery_color = COLOR_SUCCESS if t.is_mastered else COLOR_WARNING
    icon = "\u2713" if t.is_mastered else "\u25cb"
    with st.expander(f"{icon} {t.domain}: {t.target_name}", expanded=False):
        col1, col2 = st.columns(2)
        with col1:
            t.domain = st.text_input("Domain", value=t.domain, key=f"skill_domain_{i}")
            t.target_name = st.text_input("Target Name", value=t.target_name, key=f"skill_target_{i}")
            t.date_introduced = st.date_input(
                "Date Introduced", value=_date_to_value(t.date_introduced), key=f"skill_intro_{i}",
            )
            t.is_mastered = st.checkbox("Mastered", value=t.is_mastered, key=f"skill_mastered_{i}")
            if t.is_mastered:
                t.date_mastered = st.date_input(
                    "Date Mastered",
                    value=_date_to_value(t.date_mastered) or date.today(),
                    key=f"skill_mastered_date_{i}",
                )
            else:
                t.date_mastered = None

        with col2:
            t.current_accuracy_pct = st.slider(
                "Current Accuracy %", 0.0, 100.0,
                value=t.current_accuracy_pct or 0.0, key=f"skill_acc_{i}",
            )
            t.mastery_criterion_pct = st.slider(
                "Mastery Criterion %", 0.0, 100.0,
                value=t.mastery_criterion_pct, key=f"skill_crit_{i}",
            )
            t.generalization_demonstrated = st.checkbox(
                "Generalization Demonstrated",
                value=t.generalization_demonstrated, key=f"skill_gen_{i}",
            )

        val = st.text_area("Notes", value=t.notes or "", key=f"skill_notes_{i}")
        t.notes = val or None

        if st.button("Remove this target", key=f"rm_skill_{i}", type="secondary"):
            data.skill_acquisition_targets.pop(i)
            st.rerun()

if st.button("+ Add Skill Target", key="add_skill"):
    from schemas.clinical_data import SkillAcquisitionTarget
    data.skill_acquisition_targets.append(SkillAcquisitionTarget(
        domain="", target_name="", date_introduced=date.today(),
    ))
    st.rerun()

st.divider()

# ===================================================================
# 4. Behavior Reduction Targets
# ===================================================================
section_header(4, "Behavior Reduction Targets", f"{len(data.behavior_reduction_targets)} tracked")

for i, b in enumerate(data.behavior_reduction_targets):
    trend_label = b.trend.value if b.trend else "\u2014"
    trend_color = COLOR_SUCCESS if trend_label == "decreasing" else COLOR_WARNING if trend_label == "stable" else COLOR_CRITICAL
    with st.expander(f"[{trend_label}] {b.behavior_name}", expanded=False):
        col1, col2 = st.columns(2)
        with col1:
            b.behavior_name = st.text_input("Behavior Name", value=b.behavior_name, key=f"beh_name_{i}")
            b.measurement_type = st.selectbox(
                "Measurement Type",
                ["frequency", "duration", "rate", "interval", "latency"],
                index=["frequency", "duration", "rate", "interval", "latency"].index(b.measurement_type)
                if b.measurement_type in ["frequency", "duration", "rate", "interval", "latency"] else 0,
                key=f"beh_mtype_{i}",
            )
            b.unit = st.text_input("Unit", value=b.unit, key=f"beh_unit_{i}")
            trend_options = [t.value for t in BehaviorTrend]
            current_trend_idx = trend_options.index(b.trend.value) if b.trend else 0
            b.trend = BehaviorTrend(st.selectbox("Trend", trend_options, index=current_trend_idx, key=f"beh_trend_{i}"))

        with col2:
            b.baseline_value = st.number_input("Baseline Value", value=b.baseline_value or 0.0, format="%.1f", key=f"beh_base_{i}")
            b.baseline_date = st.date_input("Baseline Date", value=_date_to_value(b.baseline_date), key=f"beh_base_date_{i}")
            b.current_value = st.number_input("Current Value", value=b.current_value or 0.0, format="%.1f", key=f"beh_curr_{i}")
            b.current_date = st.date_input("Current Date", value=_date_to_value(b.current_date), key=f"beh_curr_date_{i}")

        # Reduction metric
        if b.baseline_value and b.current_value and b.baseline_value > 0:
            reduction = (1 - b.current_value / b.baseline_value) * 100
            if reduction > 0:
                st.markdown(
                    f'<div style="background:#ECFDF5; padding:8px 14px; border-radius:8px; display:inline-block;">'
                    f'<strong style="color:#059669;">Reduction from Baseline: {reduction:.0f}%</strong>'
                    f'</div>',
                    unsafe_allow_html=True,
                )

        b.operational_definition = st.text_area(
            "Operational Definition", value=b.operational_definition, height=100, key=f"beh_opdef_{i}",
        )
        val = st.text_input("Function of Behavior", value=b.function_of_behavior or "", key=f"beh_func_{i}")
        b.function_of_behavior = val or None

        strategies_str = st.text_area(
            "Intervention Strategies (one per line)",
            value="\n".join(b.intervention_strategies), height=100, key=f"beh_strat_{i}",
        )
        b.intervention_strategies = [s.strip() for s in strategies_str.split("\n") if s.strip()]

        if st.button("Remove this behavior", key=f"rm_beh_{i}", type="secondary"):
            data.behavior_reduction_targets.pop(i)
            st.rerun()

if st.button("+ Add Behavior Target", key="add_behavior"):
    from schemas.clinical_data import BehaviorReductionTarget
    data.behavior_reduction_targets.append(BehaviorReductionTarget(
        behavior_name="", operational_definition="", measurement_type="frequency", baseline_value=0.0,
    ))
    st.rerun()

st.divider()

# ===================================================================
# 5. Hours Utilization
# ===================================================================
section_header(5, "Hours Utilization", f"{len(data.hours_utilization)} codes")

for i, h in enumerate(data.hours_utilization):
    pct = h.utilization_pct or (h.utilized_units / h.authorized_units * 100 if h.authorized_units else 0)
    util_color = COLOR_CRITICAL if pct < 80 else COLOR_SUCCESS
    with st.expander(f"{h.cpt_code.value} \u2014 {h.utilized_units}/{h.authorized_units} units ({pct:.0f}%)", expanded=False):
        col1, col2, col3 = st.columns(3)
        with col1:
            cpt_options = [c.value for c in CPTCode]
            current_idx = cpt_options.index(h.cpt_code.value) if h.cpt_code.value in cpt_options else 0
            h.cpt_code = CPTCode(st.selectbox("CPT Code", cpt_options, index=current_idx, key=f"hours_cpt_{i}"))
        with col2:
            h.authorized_units = st.number_input("Authorized Units", value=float(h.authorized_units), min_value=0.0, format="%.0f", key=f"hours_auth_{i}")
        with col3:
            h.utilized_units = st.number_input("Utilized Units", value=float(h.utilized_units), min_value=0.0, format="%.0f", key=f"hours_util_{i}")

        # Auto-calculate with visual progress
        if h.authorized_units > 0:
            h.utilization_pct = round(h.utilized_units / h.authorized_units * 100, 1)
            bar_color = COLOR_SUCCESS if h.utilization_pct >= 80 else COLOR_WARNING if h.utilization_pct >= 60 else COLOR_CRITICAL
            st.markdown(
                f'<strong>Utilization:</strong> '
                + progress_bar_html(h.utilization_pct, 100, bar_color),
                unsafe_allow_html=True,
            )

        if h.utilization_pct is not None and h.utilization_pct < 80:
            h.explanation_if_low = st.text_area(
                "Explanation for Low Utilization (required < 80%)",
                value=h.explanation_if_low or "", key=f"hours_explain_{i}",
            )
            if not h.explanation_if_low:
                st.warning("Payor may require an explanation for utilization below 80%.")
        elif h.explanation_if_low:
            h.explanation_if_low = st.text_area("Explanation (optional)", value=h.explanation_if_low, key=f"hours_explain_{i}")

        if st.button("Remove", key=f"rm_hours_{i}", type="secondary"):
            data.hours_utilization.pop(i)
            st.rerun()

if st.button("+ Add Hours Entry", key="add_hours"):
    from schemas.clinical_data import HoursUtilization
    data.hours_utilization.append(HoursUtilization(
        cpt_code=CPTCode.ADAPTIVE_BEHAVIOR_97153, authorized_units=0, utilized_units=0,
    ))
    st.rerun()

st.divider()

# ===================================================================
# 6. Treatment Goals
# ===================================================================
section_header(6, "Treatment Goals", f"{len(data.treatment_goals)} goals")

for i, g in enumerate(data.treatment_goals):
    goal_color = COLOR_SUCCESS if g.status == "met" else COLOR_WARNING if g.status == "in progress" else COLOR_CRITICAL
    with st.expander(f"Goal {g.goal_number}: {g.goal_area} \u2014 {g.status}", expanded=False):
        col1, col2, col3 = st.columns(3)
        with col1:
            g.goal_number = st.number_input("Goal #", value=g.goal_number, min_value=1, key=f"goal_num_{i}")
        with col2:
            g.goal_area = st.text_input("Goal Area", value=g.goal_area, key=f"goal_area_{i}")
        with col3:
            status_options = ["in progress", "met", "modified", "discontinued"]
            idx = status_options.index(g.status) if g.status in status_options else 0
            g.status = st.selectbox("Status", status_options, index=idx, key=f"goal_status_{i}")

        g.goal_statement = st.text_area("Goal Statement", value=g.goal_statement, height=80, key=f"goal_stmt_{i}")

        val = st.text_area("Baseline Performance", value=g.baseline_performance or "", height=60, key=f"goal_base_{i}")
        g.baseline_performance = val or None

        val = st.text_area("Current Performance", value=g.current_performance or "", height=60, key=f"goal_curr_{i}")
        g.current_performance = val or None

        g.target_criterion = st.text_input("Target Criterion", value=g.target_criterion, key=f"goal_crit_{i}")

        if g.status in ("modified", "discontinued"):
            val = st.text_area(
                "Modification Rationale (required)", value=g.modification_rationale or "", height=80, key=f"goal_mod_{i}",
            )
            g.modification_rationale = val or None
            if not g.modification_rationale:
                st.warning("Rationale is required for modified/discontinued goals.")

        if st.button("Remove this goal", key=f"rm_goal_{i}", type="secondary"):
            data.treatment_goals.pop(i)
            st.rerun()

if st.button("+ Add Treatment Goal", key="add_goal"):
    from schemas.clinical_data import TreatmentGoal
    next_num = max((g.goal_number for g in data.treatment_goals), default=0) + 1
    data.treatment_goals.append(TreatmentGoal(
        goal_number=next_num, goal_area="", goal_statement="", target_criterion="", status="in progress",
    ))
    st.rerun()

st.divider()

# ===================================================================
# 7. Caregiver Training
# ===================================================================
section_header(7, "Caregiver Training")

ct = data.caregiver_training
ct.total_sessions = st.number_input("Total Sessions", value=ct.total_sessions, min_value=0, key="cg_sessions")

topics_str = st.text_area("Topics Covered (one per line)", value="\n".join(ct.topics_covered), height=120, key="cg_topics")
ct.topics_covered = [t.strip() for t in topics_str.split("\n") if t.strip()]

val = st.text_area("Caregiver Skill Acquisition", value=ct.caregiver_skill_acquisition or "", height=80, key="cg_skill")
ct.caregiver_skill_acquisition = val or None

val = st.text_area("Barriers to Participation", value=ct.barriers_to_participation or "", height=80, key="cg_barriers")
ct.barriers_to_participation = val or None

st.divider()

# ===================================================================
# 8. Discharge Plan
# ===================================================================
section_header(8, "Discharge Plan")

dp = data.discharge_plan
criteria_str = st.text_area(
    "Measurable Discharge Criteria (one per line)",
    value="\n".join(dp.measurable_criteria), height=120, key="dp_criteria",
)
dp.measurable_criteria = [c.strip() for c in criteria_str.split("\n") if c.strip()]

val = st.text_area("Transition Plan", value=dp.transition_plan or "", height=80, key="dp_transition")
dp.transition_plan = val or None

val = st.text_area("Current Discharge Readiness", value=dp.current_discharge_readiness or "", height=80, key="dp_readiness")
dp.current_discharge_readiness = val or None

st.divider()

# ===================================================================
# 9. Requested Hours
# ===================================================================
section_header(9, "Requested Hours for Next Authorization")

if data.requested_hours_by_code:
    updated_hours = {}
    items = list(data.requested_hours_by_code.items())
    cols = st.columns(min(4, len(items)))
    for j, (code, units) in enumerate(items):
        with cols[j % len(cols)]:
            updated_hours[code] = st.number_input(
                f"{code} (weekly units)", value=float(units), min_value=0.0, format="%.1f", key=f"req_hours_{code}",
            )
    data.requested_hours_by_code = updated_hours

val = st.text_area(
    "Clinical Justification for Requested Hours",
    value=data.clinical_justification_for_hours or "", height=100, key="clin_just",
)
data.clinical_justification_for_hours = val or None

st.divider()

# ===================================================================
# Confidence Notes & Missing Fields
# ===================================================================
if data.confidence_notes:
    with st.expander(f"Extraction Confidence Notes ({len(data.confidence_notes)})"):
        for note in data.confidence_notes:
            st.write(f"- {note}")

if data.missing_fields:
    with st.expander(f"Missing Fields ({len(data.missing_fields)})", expanded=True):
        for field in data.missing_fields:
            st.write(f"- {field}")

st.divider()

# ===================================================================
# Save & Continue
# ===================================================================
col1, col2, col3 = st.columns([2, 1, 1])
with col1:
    _bottom_save = st.button("Save All Changes", type="primary", use_container_width=True, key="save_bottom")

# Respond to either top or bottom save button
if _top_save or _bottom_save:
    _save_all()
    st.rerun()

with col2:
    with st.popover("Raw JSON Editor"):
        edited_json = st.text_area(
            "Full extracted data JSON:",
            value=json.dumps(data.model_dump(mode="json"), indent=2, default=str),
            height=400, key="raw_json_editor",
        )
        if st.button("Apply JSON"):
            try:
                updated = ExtractedClinicalData.model_validate_json(edited_json)
                st.session_state.clinical_data = updated
                st.rerun()
            except Exception as e:
                st.error(f"Invalid JSON: {e}")

with col3:
    st.page_link("pages/5_Generate.py", label="Continue to Generate \u2192", use_container_width=True)
