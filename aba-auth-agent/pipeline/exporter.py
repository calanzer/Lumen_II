"""Export generated narrative to Word document using docxtpl.

Supports multiple payor templates. Each payor can have its own .docx template
in the templates/ directory. If a template doesn't exist, one is auto-generated.
"""

from datetime import date
from pathlib import Path
from io import BytesIO

from docxtpl import DocxTemplate

from schemas.clinical_data import ExtractedClinicalData
from schemas.narrative import AnthemReauthNarrative, CustomNarrative, Narrative


# Registry of supported payors and their template filenames
PAYOR_TEMPLATES = {
    "anthem_blue_cross_ca": {
        "filename": "anthem_reauth.docx",
        "display_name": "Anthem Blue Cross California",
        "subtitle": "MCG Care Guidelines Format",
    },
    "aetna": {
        "filename": "aetna_reauth.docx",
        "display_name": "Aetna",
        "subtitle": "Six-Criteria Medical Necessity Format",
    },
    "optum": {
        "filename": "optum_reauth.docx",
        "display_name": "Optum / UnitedHealthcare",
        "subtitle": "Nine-Component Treatment Plan Format",
    },
    "blue_shield_ca": {
        "filename": "blue_shield_ca_reauth.docx",
        "display_name": "Blue Shield of California",
        "subtitle": "Covered California Format",
    },
    "medi_cal": {
        "filename": "medi_cal_reauth.docx",
        "display_name": "Medi-Cal Managed Care",
        "subtitle": "Carelon Behavioral Health — HCPCS Codes",
    },
}


def list_available_payors() -> dict[str, dict]:
    """Return the registry of supported payors with template availability."""
    templates_dir = Path(__file__).parent.parent / "templates"
    result = {}
    for key, info in PAYOR_TEMPLATES.items():
        template_path = templates_dir / info["filename"]
        result[key] = {
            **info,
            "template_exists": template_path.exists(),
        }
    return result


def _generate_template(payor_key: str) -> Path:
    """Generate a payor-specific Word template programmatically."""
    from docx import Document
    from docx.shared import Pt
    from docx.enum.text import WD_ALIGN_PARAGRAPH

    payor = PAYOR_TEMPLATES[payor_key]
    templates_dir = Path(__file__).parent.parent / "templates"
    templates_dir.mkdir(parents=True, exist_ok=True)
    template_path = templates_dir / payor["filename"]

    doc = Document()
    style = doc.styles["Normal"]
    style.font.name = "Calibri"
    style.font.size = Pt(11)

    # Title
    title = doc.add_heading("ABA Reauthorization Request", level=1)
    title.alignment = WD_ALIGN_PARAGRAPH.CENTER
    subtitle = doc.add_paragraph(payor["display_name"])
    subtitle.alignment = WD_ALIGN_PARAGRAPH.CENTER
    doc.add_paragraph("")

    # Header fields
    doc.add_paragraph("Client ID: {{ client_id }}")
    doc.add_paragraph("Diagnosis: {{ diagnosis }}")
    doc.add_paragraph("Authorization Period: {{ auth_period_start }} — {{ auth_period_end }}")
    doc.add_paragraph("Supervising BCBA: {{ supervising_bcba }} ({{ bcba_credential }})")
    doc.add_paragraph("Date Prepared: {{ date_prepared }}")
    doc.add_paragraph("")

    # Sections
    sections = [
        ("1. Client Overview", "{{ client_overview }}"),
        ("2. Assessment Summary", "{{ assessment_summary }}"),
        ("3. Skill Acquisition Progress", "{{ skill_acquisition_progress }}"),
        ("4. Behavior Reduction Progress", "{{ behavior_reduction_progress }}"),
        ("5. Treatment Plan Update", "{{ treatment_plan_update }}"),
        ("6. Hours Utilization & Justification", "{{ hours_justification }}"),
        ("7. Caregiver Training", "{{ caregiver_training_summary }}"),
        ("8. Medical Necessity Statement", "{{ medical_necessity }}"),
        ("9. Discharge Plan", "{{ discharge_plan }}"),
    ]

    for heading, placeholder in sections:
        doc.add_heading(heading, level=2)
        doc.add_paragraph(placeholder)
        doc.add_paragraph("")

    # Footer
    doc.add_paragraph("")
    doc.add_paragraph("Prepared by: {{ supervising_bcba }}")
    doc.add_paragraph("Credential: {{ bcba_credential }}")
    doc.add_paragraph("Date: {{ date_prepared }}")
    doc.add_paragraph("")
    disclaimer = doc.add_paragraph(
        "DISCLOSURE: This document was drafted with AI assistance and reviewed/approved "
        "by the supervising BCBA listed above."
    )
    disclaimer.runs[0].font.size = Pt(9)

    doc.save(str(template_path))
    return template_path


def get_template_path(payor_key: str = "anthem_blue_cross_ca") -> Path:
    """Get the template path for a payor, generating it if it doesn't exist."""
    if payor_key not in PAYOR_TEMPLATES:
        raise ValueError(
            f"Unknown payor '{payor_key}'. Available: {list(PAYOR_TEMPLATES.keys())}"
        )

    templates_dir = Path(__file__).parent.parent / "templates"
    template_path = templates_dir / PAYOR_TEMPLATES[payor_key]["filename"]

    if not template_path.exists():
        template_path = _generate_template(payor_key)

    return template_path


def _header_context(data: ExtractedClinicalData) -> dict:
    """Client and authorization header fields shared by all export paths."""
    return {
        "client_id": data.client.client_id or "[CLIENT ID]",
        "diagnosis": ", ".join(
            f"{code} ({desc})"
            for code, desc in zip(
                data.client.diagnosis_codes,
                data.client.diagnosis_descriptions or data.client.diagnosis_codes,
            )
        ) or "[DIAGNOSIS]",
        "auth_period_start": str(data.client.auth_period_start or "[START DATE]"),
        "auth_period_end": str(data.client.auth_period_end or "[END DATE]"),
        "supervising_bcba": data.client.supervising_bcba or "[BCBA NAME]",
        "bcba_credential": data.client.bcba_credential_number or "[CREDENTIAL #]",
        "date_prepared": date.today().isoformat(),
    }


def _split_markdown_blocks(content: str) -> list[tuple[str, object]]:
    """Split narrative text into ("p", text), ("bullet", text) and ("table", rows) blocks.

    The AI writes tables and bullet lists as light markdown; Word needs real ones.
    """
    blocks: list[tuple[str, object]] = []
    table_rows: list[list[str]] = []

    def flush_table():
        if table_rows:
            blocks.append(("table", list(table_rows)))
            table_rows.clear()

    for line in content.splitlines():
        stripped = line.strip()
        if stripped.startswith("|") and stripped.endswith("|") and len(stripped) > 1:
            cells = [cell.strip() for cell in stripped.strip("|").split("|")]
            if all(set(cell) <= set("-: ") and cell for cell in cells):
                continue  # the |---|---| divider row
            table_rows.append(cells)
            continue
        flush_table()
        if not stripped:
            continue
        if stripped[:2] in ("- ", "* "):
            blocks.append(("bullet", stripped[2:].strip()))
        else:
            blocks.append(("p", stripped))
    flush_table()
    return blocks


def _export_custom_docx(data: ExtractedClinicalData, narrative: CustomNarrative) -> bytes:
    """Render a template-driven narrative: one heading + body per template section."""
    from docx import Document
    from docx.enum.text import WD_ALIGN_PARAGRAPH
    from docx.shared import Pt

    ctx = _header_context(data)
    payor_name = PAYOR_TEMPLATES.get(narrative.payor_key, {}).get("display_name", "")

    doc = Document()
    doc.styles["Normal"].font.name = "Calibri"
    doc.styles["Normal"].font.size = Pt(11)

    title = doc.add_heading("ABA Reauthorization Request", level=1)
    title.alignment = WD_ALIGN_PARAGRAPH.CENTER
    if payor_name:
        doc.add_paragraph(payor_name).alignment = WD_ALIGN_PARAGRAPH.CENTER
    doc.add_paragraph("")

    doc.add_paragraph(f"Client ID: {ctx['client_id']}")
    doc.add_paragraph(f"Diagnosis: {ctx['diagnosis']}")
    doc.add_paragraph(f"Authorization Period: {ctx['auth_period_start']} \u2014 {ctx['auth_period_end']}")
    doc.add_paragraph(f"Supervising BCBA: {ctx['supervising_bcba']} ({ctx['bcba_credential']})")
    doc.add_paragraph(f"Date Prepared: {ctx['date_prepared']}")
    doc.add_paragraph("")

    for index, section in enumerate(narrative.sections, start=1):
        doc.add_heading(f"{index}. {section.section_name or section.key}", level=2)
        for kind, value in _split_markdown_blocks(section.content):
            if kind == "table":
                width = max(len(row) for row in value)
                table = doc.add_table(rows=len(value), cols=width)
                table.style = "Light Grid Accent 1"
                for r, row in enumerate(value):
                    for c in range(width):
                        cell = table.rows[r].cells[c]
                        cell.text = row[c] if c < len(row) else ""
                        for run in cell.paragraphs[0].runs:
                            run.font.size = Pt(9)
                            run.bold = run.bold or r == 0
            elif kind == "bullet":
                doc.add_paragraph(value, style="List Bullet")
            else:
                doc.add_paragraph(value)
        doc.add_paragraph("")

    doc.add_paragraph(f"Prepared by: {ctx['supervising_bcba']}")
    doc.add_paragraph(f"Credential: {ctx['bcba_credential']}")
    doc.add_paragraph(f"Date: {ctx['date_prepared']}")
    doc.add_paragraph("")
    disclaimer = doc.add_paragraph(
        "DISCLOSURE: This document was drafted with AI assistance and reviewed/approved "
        "by the supervising BCBA listed above."
    )
    disclaimer.runs[0].font.size = Pt(9)

    buffer = BytesIO()
    doc.save(buffer)
    buffer.seek(0)
    return buffer.getvalue()


def export_to_docx(
    data: ExtractedClinicalData,
    narrative: Narrative,
    payor_key: str = "anthem_blue_cross_ca",
) -> bytes:
    """
    Render the narrative into a Word document.

    Default narratives use the payor-specific .docx template; template-driven
    (custom) narratives are rendered from their own sections.
    Returns the document as bytes for download.
    """
    if isinstance(narrative, CustomNarrative):
        return _export_custom_docx(data, narrative)

    template_path = get_template_path(payor_key)
    doc = DocxTemplate(str(template_path))

    context = {
        **_header_context(data),
        # Narrative sections
        "client_overview": narrative.client_overview.content,
        "assessment_summary": narrative.assessment_summary.content,
        "skill_acquisition_progress": narrative.skill_acquisition_progress.content,
        "behavior_reduction_progress": narrative.behavior_reduction_progress.content,
        "treatment_plan_update": narrative.treatment_plan_update.content,
        "hours_justification": narrative.hours_justification.content,
        "caregiver_training_summary": narrative.caregiver_training_summary.content,
        "medical_necessity": narrative.medical_necessity.content,
        "discharge_plan": narrative.discharge_plan.content,
    }

    doc.render(context)

    buffer = BytesIO()
    doc.save(buffer)
    buffer.seek(0)
    return buffer.getvalue()
