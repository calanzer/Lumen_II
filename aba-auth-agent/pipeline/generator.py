"""Generate payor-specific reauthorization narratives from extracted clinical data."""

import anthropic
import json
from pathlib import Path

from pipeline.claim_check import find_discrepancies
from pipeline.llm import (
    CHECK_MODEL,
    EFFORT_GENERATE,
    EFFORT_LIGHT,
    MAIN_MODEL,
    MAX_TOKENS_LARGE,
    MAX_TOKENS_SMALL,
    response_text,
)
from schemas.clinical_data import ExtractedClinicalData
from schemas.narrative import (
    AnthemReauthNarrative,
    CustomNarrative,
    KeyedSection,
    Narrative,
    ReauthTemplate,
    get_sections,
)


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
        model=MAIN_MODEL,
        max_tokens=MAX_TOKENS_LARGE,
        output_config={"effort": EFFORT_GENERATE},
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

    raw_text = response_text(message)

    # Strip markdown fences if present
    if raw_text.startswith("```"):
        raw_text = raw_text.split("\n", 1)[1]
    if raw_text.endswith("```"):
        raw_text = raw_text.rsplit("```", 1)[0]

    parsed = json.loads(raw_text)
    return AnthemReauthNarrative.model_validate(parsed)


def extract_narrative_claims(narrative: Narrative, source_data: ExtractedClinicalData) -> list[dict]:
    """Ask a small model to list every quantitative claim in the narrative.

    Returns the model's raw claim list; find_discrepancies decides which are problems.
    """
    client = anthropic.Anthropic()

    all_narrative_text = "\n\n".join(
        section.content for _, _, section in get_sections(narrative)
    )

    message = client.messages.create(
        model=CHECK_MODEL,
        max_tokens=MAX_TOKENS_SMALL,
        output_config={"effort": EFFORT_LIGHT},
        system=load_prompt("validation_system.txt"),
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

    raw = response_text(message)
    if raw.startswith("```"):
        raw = raw.split("\n", 1)[1]
    if raw.endswith("```"):
        raw = raw.rsplit("```", 1)[0]
    return json.loads(raw)


def validate_narrative_against_source(
    narrative: Narrative,
    source_data: ExtractedClinicalData,
) -> list[str]:
    """
    Post-generation validation: use Claude Haiku to extract quantitative claims
    from the narrative and cross-check them against source data.

    Returns list of discrepancies found.
    """
    try:
        claims = extract_narrative_claims(narrative, source_data)
    except json.JSONDecodeError:
        return ["WARNING: Could not parse validation response. Manual review recommended."]
    return find_discrepancies(claims, source_data)


def build_custom_system_prompt(template: ReauthTemplate, payor_name: str) -> str:
    """Fill the custom-generation prompt with a template's sections and style."""
    sections_spec = "\n".join(
        f'{i}. key "{sec.key}" | title "{sec.title}"'
        + (f" | covers: {sec.guidance}" if sec.guidance else "")
        for i, sec in enumerate(template.sections, start=1)
    )
    return (
        load_prompt("custom_generation_system.txt")
        .replace("{payor_name}", payor_name)
        .replace("{sections_spec}", sections_spec)
        .replace("{style_notes}", template.style_notes or "No specific style notes provided.")
    )


def assemble_custom_narrative(
    parsed: dict, template: ReauthTemplate, payor_key: str = ""
) -> CustomNarrative:
    """Build a CustomNarrative from model output, guaranteeing every template section.

    Sections come back in template order. A section the model skipped becomes a
    flagged placeholder so it can't silently vanish from the report.
    """
    returned = {str(sec.get("key")): sec for sec in parsed.get("sections", []) if isinstance(sec, dict)}
    sections: list[KeyedSection] = []
    for tsec in template.sections:
        got = returned.get(tsec.key)
        if got and str(got.get("content") or "").strip():
            sections.append(
                KeyedSection(
                    key=tsec.key,
                    section_name=tsec.title,
                    content=str(got["content"]),
                    source_data_keys=[str(k) for k in got.get("source_data_keys") or []],
                    requires_review=bool(got.get("requires_review", False)),
                    review_note=got.get("review_note"),
                )
            )
        else:
            sections.append(
                KeyedSection(
                    key=tsec.key,
                    section_name=tsec.title,
                    content=f"[SECTION NOT GENERATED — CLINICIAN ACTION REQUIRED: write the {tsec.title} section]",
                    requires_review=True,
                    review_note="The AI did not return this section.",
                )
            )

    confidence = parsed.get("overall_confidence", 0.0)
    try:
        confidence = min(max(float(confidence), 0.0), 1.0)
    except (TypeError, ValueError):
        confidence = 0.0

    return CustomNarrative(
        payor_key=payor_key,
        template_name=template.name,
        sections=sections,
        overall_confidence=confidence,
        flags_for_bcba=[str(f) for f in parsed.get("flags_for_bcba") or []],
    )


def generate_custom_narrative(
    data: ExtractedClinicalData,
    template: ReauthTemplate,
    payor_name: str,
    payor_key: str = "",
) -> CustomNarrative:
    """Generate a narrative that follows a practice-supplied template."""
    client = anthropic.Anthropic()

    message = client.messages.create(
        model=MAIN_MODEL,
        max_tokens=MAX_TOKENS_LARGE,
        output_config={"effort": EFFORT_GENERATE},
        system=[
            {
                "type": "text",
                "text": build_custom_system_prompt(template, payor_name),
                "cache_control": {"type": "ephemeral"},
            }
        ],
        messages=[
            {
                "role": "user",
                "content": (
                    f"<clinical_data>\n{data.model_dump_json(indent=2)}\n</clinical_data>\n\n"
                    f"Generate the complete {payor_name} reauthorization narrative from the "
                    "clinical data above, following the report structure and output format exactly."
                ),
            }
        ],
    )

    raw_text = response_text(message)
    if raw_text.startswith("```"):
        raw_text = raw_text.split("\n", 1)[1]
    if raw_text.endswith("```"):
        raw_text = raw_text.rsplit("```", 1)[0]

    return assemble_custom_narrative(json.loads(raw_text), template, payor_key)

