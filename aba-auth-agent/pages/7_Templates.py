"""Page 7: Template library — teach the app a payor's report format from a past report.

Upload a report the practice has written before; the app keeps only its structure
(section titles, what each covers) and writing style. The uploaded file is not stored.
"""

import pandas as pd
import streamlit as st

from data.store import clear_active_template, get_active_template, save_template
from pipeline.exporter import list_available_payors
from pipeline.template_extractor import extract_template_structure, sections_from_rows
from schemas.narrative import ANTHEM_SECTIONS
from ui_style import inject_custom_css, branded_header

inject_custom_css()

branded_header("Templates", "Teach the app how each payor's reauthorization report should be laid out.")

payors = list_available_payors()
payor = st.selectbox(
    "Payor",
    list(payors.keys()),
    format_func=lambda k: payors[k]["display_name"],
)
payor_name = payors[payor]["display_name"]
draft_key = f"tpl_draft_{payor}"

# --- Current template ---
active = get_active_template(payor)
with st.container(border=True):
    if active:
        st.markdown(f"**Using your template:** {active.name}")
        st.caption(f"{len(active.sections)} sections. New narratives for {payor_name} clients follow this layout.")
        for i, sec in enumerate(active.sections, start=1):
            st.markdown(f"{i}. **{sec.title}**" + (f" — {sec.guidance}" if sec.guidance else ""))
        if active.style_notes:
            st.caption(f"Style: {active.style_notes}")
        if st.button("Use the built-in default instead", key=f"reset_{payor}"):
            clear_active_template(payor)
            st.session_state.pop(draft_key, None)
            st.rerun()
    else:
        st.markdown("**Using the built-in default layout**")
        st.caption("Nine standard sections: " + ", ".join(title for _, title in ANTHEM_SECTIONS) + ".")

# --- Upload a past report ---
st.markdown("### Create a template from a past report")
st.caption(
    "Upload a reauthorization report your practice has written for this payor. "
    "Only its section structure and writing style are kept. Client details are not copied, "
    "and the uploaded file is not stored."
)

uploaded = st.file_uploader("Past report", type=["pdf", "docx"], key=f"tpl_upload_{payor}")

if uploaded and st.button("Analyze report", type="primary"):
    with st.spinner("Reading the report's structure... (10-30 seconds)"):
        try:
            result = extract_template_structure(uploaded.getvalue(), uploaded.name)
        except Exception as e:
            st.error(f"Could not analyze that report: {e}")
        else:
            st.session_state[draft_key] = {
                "sections": [s.model_dump() for s in result["sections"]],
                "style_notes": result["style_notes"],
                "source_filename": uploaded.name,
            }
            st.rerun()

# --- Review and edit the detected structure ---
draft = st.session_state.get(draft_key)
if draft:
    st.markdown("### Review the detected sections")
    st.caption(
        "Fix titles, edit what each section covers, add or delete rows, and change the Order numbers "
        "to rearrange. Nothing is saved until you click Save template."
    )

    table = pd.DataFrame(
        {
            "Order": list(range(1, len(draft["sections"]) + 1)),
            "Title": [s["title"] for s in draft["sections"]],
            "Covers": [s["guidance"] for s in draft["sections"]],
        }
    )
    edited = st.data_editor(
        table,
        num_rows="dynamic",
        hide_index=True,
        width="stretch",
        key=f"tpl_editor_{payor}",
        column_config={
            "Order": st.column_config.NumberColumn("Order", min_value=1, step=1, width="small"),
            "Title": st.column_config.TextColumn("Title", required=True),
            "Covers": st.column_config.TextColumn("What it covers", width="large"),
        },
    )

    style_notes = st.text_area("Writing style", value=draft["style_notes"], height=100, key=f"tpl_style_{payor}")
    name = st.text_input(
        "Template name",
        value=f"{payor_name} — {draft['source_filename']}",
        key=f"tpl_name_{payor}",
    )

    with st.container(horizontal=True):
        if st.button("Save template", type="primary", key=f"tpl_save_{payor}"):
            ordered = edited.assign(Order=pd.to_numeric(edited["Order"], errors="coerce")).sort_values(
                "Order", kind="stable", na_position="last"
            )
            sections = sections_from_rows(
                [
                    {"title": row["Title"], "guidance": row["Covers"]}
                    for _, row in ordered.iterrows()
                    if pd.notna(row["Title"])
                ]
            )
            if len(sections) < 2:
                st.error("A template needs at least two sections.")
            elif not name.strip():
                st.error("Give the template a name.")
            else:
                save_template(
                    payor, name.strip(), sections, style_notes.strip(), draft["source_filename"]
                )
                st.session_state.pop(draft_key, None)
                st.toast(f"Template saved for {payor_name}.", icon="✅")
                st.rerun()
        if st.button("Discard", key=f"tpl_discard_{payor}"):
            st.session_state.pop(draft_key, None)
            st.rerun()
