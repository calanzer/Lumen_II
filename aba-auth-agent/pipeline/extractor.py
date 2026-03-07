"""Extract structured clinical data from ABA progress reports (PDF or DOCX) using Claude API.

Pipeline: classify -> Claude Sonnet (extract to JSON) -> cross-validate tables -> Pydantic (enforce schema)
"""

import anthropic
import base64
import json
import re
from datetime import datetime
from io import BytesIO
from pathlib import Path

import pdfplumber
from docx import Document

from schemas.clinical_data import ExtractedClinicalData


def load_prompt(name: str) -> str:
    """Load a prompt template from the prompts/ directory."""
    path = Path(__file__).parent.parent / "prompts" / name
    return path.read_text()


def _extract_tables_with_pdfplumber(pdf_bytes: bytes) -> list[list[list[str]]]:
    """
    Use pdfplumber to deterministically extract all tables from the PDF.
    Returns a list of tables, where each table is a list of rows (list of cell strings).
    """
    tables = []
    with pdfplumber.open(pdf_bytes) as pdf:
        for page in pdf.pages:
            page_tables = page.extract_tables()
            if page_tables:
                for table in page_tables:
                    # Clean None cells to empty strings
                    cleaned = [
                        [cell.strip() if cell else "" for cell in row]
                        for row in table
                        if row  # skip empty rows
                    ]
                    if cleaned:
                        tables.append(cleaned)
    return tables


def _extract_tables_from_docx(docx_bytes: bytes) -> list[list[list[str]]]:
    """
    Extract all tables from a DOCX file.
    Returns same format as _extract_tables_with_pdfplumber.
    """
    doc = Document(BytesIO(docx_bytes))
    tables = []
    for table in doc.tables:
        rows = []
        for row in table.rows:
            cells = [cell.text.strip() for cell in row.cells]
            if any(cells):  # skip empty rows
                rows.append(cells)
        if rows:
            tables.append(rows)
    return tables


def _extract_text_from_docx(docx_bytes: bytes) -> str:
    """
    Extract full text content from a DOCX file, including table data.
    Preserves structure with section headers and table formatting.
    """
    doc = Document(BytesIO(docx_bytes))
    parts = []

    for element in doc.element.body:
        tag = element.tag.split("}")[-1] if "}" in element.tag else element.tag

        if tag == "p":
            # Paragraph
            para = element
            text = "".join(node.text or "" for node in para.iter() if node.text)
            if text.strip():
                parts.append(text.strip())

        elif tag == "tbl":
            # Table — render as pipe-delimited for clarity to the LLM
            for tr in element.iter():
                tr_tag = tr.tag.split("}")[-1] if "}" in tr.tag else tr.tag
                if tr_tag == "tr":
                    cells = []
                    for tc in tr.iter():
                        tc_tag = tc.tag.split("}")[-1] if "}" in tc.tag else tc.tag
                        if tc_tag == "tc":
                            cell_text = "".join(
                                node.text or "" for node in tc.iter() if node.text
                            ).strip()
                            cells.append(cell_text)
                    if cells:
                        parts.append(" | ".join(cells))

    return "\n".join(parts)


def _cross_validate_tables(
    extracted: dict,
    tables: list[list[list[str]]],
) -> list[str]:
    """
    Cross-validate Claude's extraction against deterministic table extraction.
    Checks that critical numeric values from tables appear in the extracted data.

    Returns list of discrepancy notes to add to confidence_notes.
    """
    discrepancies = []
    extracted_json = json.dumps(extracted, default=str)

    for table_idx, table in enumerate(tables):
        if not table or len(table) < 2:
            continue

        header = [h.lower() for h in table[0]]

        # Check for hours/utilization tables
        is_hours_table = any(
            kw in " ".join(header)
            for kw in ["cpt", "authorized", "utilized", "units", "hours", "hcpcs"]
        )
        if is_hours_table:
            for row in table[1:]:
                for cell in row:
                    # Look for numeric values that should appear in extraction
                    numbers = re.findall(r'\b\d+\.?\d*\b', cell)
                    for num in numbers:
                        if float(num) > 0 and num not in extracted_json:
                            discrepancies.append(
                                f"Table cross-validation: value '{num}' found in hours/utilization table "
                                f"but not in extracted data. Verify hours_utilization accuracy."
                            )
                            break  # One warning per table is enough
                if discrepancies:
                    break

        # Check for assessment score tables
        is_assessment_table = any(
            kw in " ".join(header)
            for kw in ["score", "percentile", "standard", "domain", "vb-mapp", "ablls", "vineland"]
        )
        if is_assessment_table:
            for row in table[1:]:
                for cell in row:
                    numbers = re.findall(r'\b\d+\.?\d*\b', cell)
                    for num in numbers:
                        if float(num) > 0 and num not in extracted_json:
                            discrepancies.append(
                                f"Table cross-validation: value '{num}' found in assessment table "
                                f"but not in extracted data. Verify assessment scores."
                            )
                            break
                if discrepancies and len(discrepancies) > 1:
                    break

    return discrepancies


def _strip_markdown_fences(text: str) -> str:
    """Remove markdown code fences from LLM response."""
    text = text.strip()
    if text.startswith("```"):
        text = text.split("\n", 1)[1]
    if text.endswith("```"):
        text = text.rsplit("```", 1)[0]
    return text.strip()


def _build_content_blocks_for_pdf(pdf_bytes: bytes) -> list[dict]:
    """Build Claude API content blocks for a PDF document."""
    pdf_b64 = base64.standard_b64encode(pdf_bytes).decode("utf-8")
    return [
        {
            "type": "document",
            "source": {
                "type": "base64",
                "media_type": "application/pdf",
                "data": pdf_b64,
            },
        },
    ]


def _build_content_blocks_for_docx(docx_bytes: bytes) -> list[dict]:
    """Build Claude API content blocks for a DOCX document (sent as extracted text)."""
    text = _extract_text_from_docx(docx_bytes)
    return [
        {
            "type": "text",
            "text": (
                "<document_content format=\"docx_extracted_text\">\n"
                f"{text}\n"
                "</document_content>"
            ),
        },
    ]


def extract_clinical_data(file_bytes: bytes, filename: str) -> ExtractedClinicalData:
    """
    Send document (PDF or DOCX) to Claude API for structured clinical data extraction,
    then cross-validate tabular data.

    For PDFs: uses Claude's native PDF support (base64-encoded document block).
    For DOCX: extracts text and tables, sends as structured text content.

    Returns validated Pydantic model.
    """
    client = anthropic.Anthropic()
    system_prompt = load_prompt("extraction_system.txt")

    is_docx = filename.lower().endswith(".docx")

    # Build content blocks based on file type
    if is_docx:
        doc_blocks = _build_content_blocks_for_docx(file_bytes)
    else:
        doc_blocks = _build_content_blocks_for_pdf(file_bytes)

    instruction_block = {
        "type": "text",
        "text": (
            "Extract all clinical data from this ABA progress report into the JSON schema. "
            "Be thorough — capture every skill acquisition target, every behavior reduction target, "
            "every assessment score, and all hours utilization data. "
            "If a field is not present in the document, set it to null. "
            "If you are uncertain about a value, include it in confidence_notes. "
            "Respond with ONLY valid JSON matching the schema — no markdown, no explanation."
        ),
    }

    # Use prompt caching on the system prompt (large, reused across calls)
    message = client.messages.create(
        model="claude-sonnet-4-20250514",
        max_tokens=8000,
        system=[
            {
                "type": "text",
                "text": system_prompt,
                "cache_control": {"type": "ephemeral"},
            }
        ],
        messages=[
            {
                "role": "user",
                "content": doc_blocks + [instruction_block],
            }
        ],
    )

    # Parse response
    raw_text = _strip_markdown_fences(message.content[0].text)
    data = json.loads(raw_text)

    # Inject metadata
    data["source_filename"] = filename
    data["extraction_timestamp"] = datetime.utcnow().isoformat()
    data["extraction_model"] = "claude-sonnet-4-20250514"

    # Cross-validate with deterministic table extraction
    try:
        if is_docx:
            tables = _extract_tables_from_docx(file_bytes)
        else:
            tables = _extract_tables_with_pdfplumber(file_bytes)
        if tables:
            table_discrepancies = _cross_validate_tables(data, tables)
            if table_discrepancies:
                existing_notes = data.get("confidence_notes", []) or []
                data["confidence_notes"] = existing_notes + table_discrepancies
    except Exception:
        # Table validation is best-effort; don't block extraction on failure
        existing_notes = data.get("confidence_notes", []) or []
        data["confidence_notes"] = existing_notes + [
            "Table cross-validation could not be performed."
        ]

    # Validate against Pydantic schema
    return ExtractedClinicalData.model_validate(data)
