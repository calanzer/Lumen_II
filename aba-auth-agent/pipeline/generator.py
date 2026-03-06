"""Generate payor-specific reauthorization narratives from extracted clinical data."""

import anthropic
import json
from pathlib import Path

from schemas.clinical_data import ExtractedClinicalData
from schemas.narrative import AnthemReauthNarrative


def load_prompt(name: str) -> str:
    path = Path(__file__).parent.parent / "prompts" / name
    return path.read_text()


def generate_narrative(data: ExtractedClinicalData) -> AnthemReauthNarrative:
    """
    Generate Anthem Blue Cross CA reauthorization narrative from extracted clinical data.

    Uses prompt caching on the system prompt for ~90% cost savings on repeated calls.
    """
    client = anthropic.Anthropic()
    system_prompt = load_prompt("generation_system.txt")

    # Serialize clinical data for the prompt
    clinical_json = data.model_dump_json(indent=2)

    message = client.messages.create(
        model="claude-sonnet-4-20250514",
        max_tokens=8000,
        temperature=0.2,  # Low temperature for clinical accuracy
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
                "content": (
                    f"<clinical_data>\n{clinical_json}\n</clinical_data>\n\n"
                    "Generate the complete Anthem Blue Cross CA reauthorization narrative "
                    "based on the clinical data above. Follow the output format exactly."
                ),
            }
        ],
    )

    raw_text = message.content[0].text

    # Strip markdown fences if present
    raw_text = raw_text.strip()
    if raw_text.startswith("```"):
        raw_text = raw_text.split("\n", 1)[1]
    if raw_text.endswith("```"):
        raw_text = raw_text.rsplit("```", 1)[0]

    parsed = json.loads(raw_text)
    return AnthemReauthNarrative.model_validate(parsed)


def validate_narrative_against_source(
    narrative: AnthemReauthNarrative,
    source_data: ExtractedClinicalData,
) -> list[str]:
    """
    Post-generation validation: use Claude Haiku to extract quantitative claims
    from the narrative and cross-check against source data.

    Returns list of discrepancies found.
    """
    client = anthropic.Anthropic()

    # Collect all narrative text
    all_narrative_text = "\n\n".join([
        narrative.client_overview.content,
        narrative.assessment_summary.content,
        narrative.skill_acquisition_progress.content,
        narrative.behavior_reduction_progress.content,
        narrative.treatment_plan_update.content,
        narrative.hours_justification.content,
        narrative.caregiver_training_summary.content,
        narrative.medical_necessity.content,
        narrative.discharge_plan.content,
    ])

    validation_prompt = load_prompt("validation_system.txt")

    message = client.messages.create(
        model="claude-haiku-4-5-20251001",
        max_tokens=4000,
        temperature=0.0,
        system=validation_prompt,
        messages=[
            {
                "role": "user",
                "content": (
                    f"<narrative>\n{all_narrative_text}\n</narrative>\n\n"
                    f"<source_data>\n{source_data.model_dump_json(indent=2)}\n</source_data>\n\n"
                    "Extract all quantitative claims from the narrative and cross-check "
                    "against the source data. Return discrepancies."
                ),
            }
        ],
    )

    raw = message.content[0].text
    raw = raw.strip()
    if raw.startswith("```"):
        raw = raw.split("\n", 1)[1]
    if raw.endswith("```"):
        raw = raw.rsplit("```", 1)[0]

    try:
        claims = json.loads(raw)
    except json.JSONDecodeError:
        return ["WARNING: Could not parse validation response. Manual review recommended."]

    # Cross-check claims against source data
    discrepancies = []
    source_json = source_data.model_dump_json()

    for claim in claims:
        value_str = str(claim.get("value", ""))
        found = claim.get("found_in_source", True)
        if value_str and (not found or value_str not in source_json):
            discrepancies.append(
                f"[{claim.get('section', '?')}] Claim: {claim.get('claim', '?')} "
                f"(value: {value_str}) — not found verbatim in source data. Verify manually."
            )

    return discrepancies
