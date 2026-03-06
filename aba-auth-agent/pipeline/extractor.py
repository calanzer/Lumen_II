"""Extract structured clinical data from ABA progress report PDFs using Claude API.

Pipeline: PyMuPDF (classify) -> Claude Sonnet (extract to JSON) -> pdfplumber (validate tables) -> Pydantic (enforce schema)
"""

import anthropic
import base64
import json
import re
from datetime import datetime
from pathlib import Path

import pdfplumber

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


def _cross_validate_tables(
    extracted: dict,
    tables: list[list[list[str]]],
) -> list[str]:
    """
    Cross-validate Claude's extraction against pdfplumber's deterministic table extraction.
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


def extract_clinical_data(pdf_bytes: bytes, filename: str) -> ExtractedClinicalData:
    """
    Send PDF to Claude API for structured clinical data extraction,
    then cross-validate tabular data with pdfplumber.

    Uses Claude's native PDF support (base64-encoded document block).
    Returns validated Pydantic model.
    """
    client = anthropic.Anthropic()

    system_prompt = load_prompt("extraction_system.txt")

    # Encode PDF as base64 for Claude's document processing
    pdf_b64 = base64.standard_b64encode(pdf_bytes).decode("utf-8")

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
                "content": [
                    {
                        "type": "document",
                        "source": {
                            "type": "base64",
                            "media_type": "application/pdf",
                            "data": pdf_b64,
                        },
                    },
                    {
                        "type": "text",
                        "text": (
                            "Extract all clinical data from this ABA progress report into the JSON schema. "
                            "Be thorough — capture every skill acquisition target, every behavior reduction target, "
                            "every assessment score, and all hours utilization data. "
                            "If a field is not present in the document, set it to null. "
                            "If you are uncertain about a value, include it in confidence_notes. "
                            "Respond with ONLY valid JSON matching the schema — no markdown, no explanation."
                        ),
                    },
                ],
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

    # Cross-validate with pdfplumber table extraction
    try:
        tables = _extract_tables_with_pdfplumber(pdf_bytes)
        if tables:
            table_discrepancies = _cross_validate_tables(data, tables)
            if table_discrepancies:
                existing_notes = data.get("confidence_notes", []) or []
                data["confidence_notes"] = existing_notes + table_discrepancies
    except Exception:
        # pdfplumber validation is best-effort; don't block extraction on failure
        existing_notes = data.get("confidence_notes", []) or []
        data["confidence_notes"] = existing_notes + [
            "pdfplumber table cross-validation could not be performed."
        ]

    # Validate against Pydantic schema
    return ExtractedClinicalData.model_validate(data)
