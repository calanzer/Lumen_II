"""Extract structured clinical data from ABA progress report PDFs using Claude API."""

import anthropic
import base64
import json
from datetime import datetime
from pathlib import Path

from schemas.clinical_data import ExtractedClinicalData


def load_prompt(name: str) -> str:
    """Load a prompt template from the prompts/ directory."""
    path = Path(__file__).parent.parent / "prompts" / name
    return path.read_text()


def extract_clinical_data(pdf_bytes: bytes, filename: str) -> ExtractedClinicalData:
    """
    Send PDF to Claude API for structured clinical data extraction.

    Uses Claude's native PDF support (base64-encoded document block).
    Returns validated Pydantic model.
    """
    client = anthropic.Anthropic()  # reads ANTHROPIC_API_KEY from env

    system_prompt = load_prompt("extraction_system.txt")

    # Encode PDF as base64 for Claude's document processing
    pdf_b64 = base64.standard_b64encode(pdf_bytes).decode("utf-8")

    message = client.messages.create(
        model="claude-sonnet-4-20250514",
        max_tokens=8000,
        system=system_prompt,
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
    raw_text = message.content[0].text

    # Strip markdown fences if present
    if raw_text.startswith("```"):
        raw_text = raw_text.split("\n", 1)[1]
        if raw_text.endswith("```"):
            raw_text = raw_text.rsplit("```", 1)[0]

    data = json.loads(raw_text)

    # Inject metadata
    data["source_filename"] = filename
    data["extraction_timestamp"] = datetime.utcnow().isoformat()
    data["extraction_model"] = "claude-sonnet-4-20250514"

    # Validate against Pydantic schema
    return ExtractedClinicalData.model_validate(data)
