"""Tests for the practice-template library: structure extraction, storage,
template-driven generation assembly, and Word export."""

import io
import json
import os
from pathlib import Path
from types import SimpleNamespace

import pytest
from docx import Document

from schemas.clinical_data import ExtractedClinicalData
from schemas.narrative import (
    ANTHEM_SECTIONS,
    AnthemReauthNarrative,
    CustomNarrative,
    ReauthTemplate,
    TemplateSection,
    get_sections,
    parse_narrative,
)

FIXTURES = Path(__file__).parent / "fixtures"
TEST_DB_PATH = FIXTURES / "test_templates.db"


@pytest.fixture(autouse=True)
def clean_db(monkeypatch):
    monkeypatch.setattr("data.store.DB_PATH", TEST_DB_PATH)
    from data.store import init_db

    init_db()
    yield
    if TEST_DB_PATH.exists():
        os.remove(TEST_DB_PATH)
    for suffix in ("-wal", "-shm"):
        extra = Path(str(TEST_DB_PATH) + suffix)
        if extra.exists():
            os.remove(extra)


@pytest.fixture
def clinical_data():
    with open(FIXTURES / "realistic_extraction.json") as f:
        return ExtractedClinicalData.model_validate(json.load(f))


@pytest.fixture
def anthem_narrative():
    with open(FIXTURES / "realistic_narrative.json") as f:
        return AnthemReauthNarrative.model_validate(json.load(f))


@pytest.fixture
def template():
    return ReauthTemplate(
        payor="aetna",
        name="Aetna — our report",
        style_notes="Third person, concise.",
        sections=[
            TemplateSection(key="summary", title="Clinical Summary", guidance="Overview of the client"),
            TemplateSection(key="medical_necessity", title="Medical Necessity", guidance="Why ABA is needed"),
            TemplateSection(key="plan", title="Plan", guidance=""),
        ],
    )


# --- sections_from_rows ---

class TestSectionsFromRows:
    def test_builds_unique_slug_keys(self):
        from pipeline.template_extractor import sections_from_rows

        sections = sections_from_rows(
            [
                {"title": "Goals & Progress", "guidance": "a"},
                {"title": "Goals & Progress", "guidance": "b"},
                {"title": "  Plan  "},
            ]
        )
        assert [s.key for s in sections] == ["goals_progress", "goals_progress_2", "plan"]
        assert sections[2].title == "Plan"
        assert sections[2].guidance == ""

    def test_drops_blank_titles_and_caps_length(self):
        from pipeline.template_extractor import MAX_SECTIONS, sections_from_rows

        rows = [{"title": ""}, {"title": None}] + [{"title": f"S{i}"} for i in range(40)]
        assert len(sections_from_rows(rows)) == MAX_SECTIONS


# --- extract_template_structure (API mocked) ---

class TestExtractTemplateStructure:
    def _patch_client(self, monkeypatch, reply_text):
        captured = {}

        class FakeMessages:
            def create(self, **kwargs):
                captured.update(kwargs)
                # Real responses may lead with a (here empty) thinking block
                return SimpleNamespace(
                    stop_reason="end_turn",
                    content=[
                        SimpleNamespace(type="thinking", thinking=""),
                        SimpleNamespace(type="text", text=reply_text),
                    ],
                )

        monkeypatch.setattr(
            "pipeline.template_extractor.anthropic.Anthropic",
            lambda: SimpleNamespace(messages=FakeMessages()),
        )
        return captured

    def test_parses_sections_and_style(self, monkeypatch):
        from pipeline.template_extractor import extract_template_structure

        reply = '```json\n' + json.dumps(
            {
                "sections": [
                    {"title": "Background", "guidance": "History"},
                    {"title": "Progress", "guidance": "Data"},
                ],
                "style_notes": "Formal.",
            }
        ) + "\n```"
        captured = self._patch_client(monkeypatch, reply)

        result = extract_template_structure(b"%PDF-fake", "old.pdf")

        assert [s.title for s in result["sections"]] == ["Background", "Progress"]
        assert result["style_notes"] == "Formal."
        # The prompt must forbid copying client details
        assert "PRIVACY" in captured["system"]

    def test_rejects_report_with_too_few_sections(self, monkeypatch):
        from pipeline.template_extractor import extract_template_structure

        self._patch_client(monkeypatch, json.dumps({"sections": [{"title": "Only one"}], "style_notes": ""}))
        with pytest.raises(ValueError):
            extract_template_structure(b"%PDF-fake", "old.pdf")


# --- storage ---

class TestTemplateStorage:
    def test_no_template_by_default(self):
        from data.store import get_active_template

        assert get_active_template("aetna") is None

    def test_save_and_load_roundtrip(self, template):
        from data.store import get_active_template, save_template

        save_template("aetna", template.name, template.sections, template.style_notes, "old.pdf")
        loaded = get_active_template("aetna")
        assert loaded.name == template.name
        assert [s.key for s in loaded.sections] == ["summary", "medical_necessity", "plan"]
        assert loaded.sections[0].guidance == "Overview of the client"
        assert loaded.style_notes == "Third person, concise."
        assert loaded.source_filename == "old.pdf"

    def test_newest_template_replaces_active_one_per_payor(self, template):
        from data.store import get_active_template, save_template

        save_template("aetna", "first", template.sections)
        save_template("aetna", "second", template.sections)
        save_template("optum", "other payor", template.sections)
        assert get_active_template("aetna").name == "second"
        assert get_active_template("optum").name == "other payor"

    def test_clear_returns_to_default_without_touching_other_payors(self, template):
        from data.store import clear_active_template, get_active_template, save_template

        save_template("aetna", "a", template.sections)
        save_template("optum", "o", template.sections)
        clear_active_template("aetna")
        assert get_active_template("aetna") is None
        assert get_active_template("optum").name == "o"


# --- assembling a custom narrative ---

class TestAssembleCustomNarrative:
    def test_sections_follow_template_order_and_titles(self, template):
        from pipeline.generator import assemble_custom_narrative

        parsed = {
            "sections": [
                {"key": "plan", "section_name": "ignored", "content": "Plan text"},
                {"key": "summary", "content": "Summary text", "source_data_keys": ["client"]},
                {"key": "medical_necessity", "content": "Necessity text", "requires_review": True, "review_note": "check"},
            ],
            "overall_confidence": 0.9,
            "flags_for_bcba": ["verify hours"],
        }
        n = assemble_custom_narrative(parsed, template, "aetna")

        assert [s.key for s in n.sections] == ["summary", "medical_necessity", "plan"]
        assert [s.section_name for s in n.sections] == ["Clinical Summary", "Medical Necessity", "Plan"]
        assert n.sections[0].source_data_keys == ["client"]
        assert n.sections[1].requires_review and n.sections[1].review_note == "check"
        assert n.payor_key == "aetna" and n.template_name == template.name
        assert n.overall_confidence == 0.9 and n.flags_for_bcba == ["verify hours"]

    def test_skipped_section_becomes_flagged_placeholder(self, template):
        from pipeline.generator import assemble_custom_narrative

        n = assemble_custom_narrative(
            {"sections": [{"key": "summary", "content": "ok"}], "overall_confidence": 0.5}, template
        )
        missing = [s for s in n.sections if s.key != "summary"]
        assert len(n.sections) == 3
        assert all(s.requires_review and "CLINICIAN ACTION REQUIRED" in s.content for s in missing)

    def test_bad_confidence_is_clamped(self, template):
        from pipeline.generator import assemble_custom_narrative

        assert assemble_custom_narrative({"sections": [], "overall_confidence": 7}, template).overall_confidence == 1.0
        assert assemble_custom_narrative({"sections": [], "overall_confidence": "high"}, template).overall_confidence == 0.0

    def test_system_prompt_includes_sections_and_style(self, template):
        from pipeline.generator import build_custom_system_prompt

        prompt = build_custom_system_prompt(template, "Aetna")
        assert "Aetna" in prompt
        assert 'key "medical_necessity"' in prompt and "covers: Why ABA is needed" in prompt
        assert "Third person, concise." in prompt
        assert "{sections_spec}" not in prompt and "{payor_name}" not in prompt


# --- uniform section access and storage of both narrative types ---

class TestNarrativeTypes:
    def test_get_sections_for_default_narrative(self, anthem_narrative):
        sections = get_sections(anthem_narrative)
        assert [(k, t) for k, t, _ in sections] == ANTHEM_SECTIONS

    def test_parse_narrative_picks_the_right_type(self, anthem_narrative, template):
        from pipeline.generator import assemble_custom_narrative

        assert isinstance(parse_narrative(anthem_narrative.model_dump_json()), AnthemReauthNarrative)
        custom = assemble_custom_narrative({"sections": [{"key": "summary", "content": "x"}]}, template, "aetna")
        assert isinstance(parse_narrative(custom.model_dump_json()), CustomNarrative)

    def test_custom_narrative_roundtrips_through_period_storage(self, template):
        from data.store import create_auth_period, create_client, get_auth_period, save_narrative
        from pipeline.generator import assemble_custom_narrative

        client_id = create_client(display_name="Test, T.", payor="aetna")
        period_id = create_auth_period(client_id, "2025-01-01", "2025-06-30")
        custom = assemble_custom_narrative(
            {"sections": [{"key": "summary", "content": "Hello"}], "overall_confidence": 0.8}, template, "aetna"
        )
        save_narrative(period_id, custom)

        loaded = get_auth_period(period_id)["narrative_data_parsed"]
        assert isinstance(loaded, CustomNarrative)
        assert loaded.sections[0].content == "Hello"

    def test_default_narrative_still_roundtrips_through_period_storage(self, anthem_narrative):
        from data.store import create_auth_period, create_client, get_auth_period, save_narrative

        client_id = create_client(display_name="Test, T.")
        period_id = create_auth_period(client_id, "2025-01-01", "2025-06-30")
        save_narrative(period_id, anthem_narrative)
        assert isinstance(get_auth_period(period_id)["narrative_data_parsed"], AnthemReauthNarrative)


# --- export ---

class TestCustomExport:
    def test_docx_contains_template_sections_in_order(self, clinical_data, template):
        from pipeline.exporter import export_to_docx
        from pipeline.generator import assemble_custom_narrative

        narrative = assemble_custom_narrative(
            {
                "sections": [
                    {"key": "summary", "content": "Alpha paragraph.\n\nSecond paragraph."},
                    {"key": "medical_necessity", "content": "Beta text."},
                    {"key": "plan", "content": "Gamma text."},
                ]
            },
            template,
            "aetna",
        )
        doc = Document(io.BytesIO(export_to_docx(clinical_data, narrative)))
        text = "\n".join(p.text for p in doc.paragraphs)

        assert "Aetna" in text
        assert "1. Clinical Summary" in text and "3. Plan" in text
        assert text.index("Alpha paragraph.") < text.index("Beta text.") < text.index("Gamma text.")
        assert "Second paragraph." in text
        assert "drafted with AI assistance" in text


class TestMarkdownInExport:
    def test_splits_tables_bullets_and_paragraphs(self):
        from pipeline.exporter import _split_markdown_blocks

        blocks = _split_markdown_blocks(
            "Intro line.\n\n| Goal | Status |\n|---|---|\n| Dress | Met |\n| Play | In progress |\n\n- first\n* second\nClosing."
        )
        assert blocks == [
            ("p", "Intro line."),
            ("table", [["Goal", "Status"], ["Dress", "Met"], ["Play", "In progress"]]),
            ("bullet", "first"),
            ("bullet", "second"),
            ("p", "Closing."),
        ]

    def test_docx_has_real_table_and_no_raw_pipes(self, clinical_data, template):
        from pipeline.exporter import export_to_docx
        from pipeline.generator import assemble_custom_narrative

        narrative = assemble_custom_narrative(
            {
                "sections": [
                    {"key": "summary", "content": "| Goal | Status |\n|---|---|\n| Dress | Met |"},
                    {"key": "medical_necessity", "content": "- Risk of regression\n- Core deficits"},
                    {"key": "plan", "content": "Plain text."},
                ]
            },
            template,
            "aetna",
        )
        doc = Document(io.BytesIO(export_to_docx(clinical_data, narrative)))

        cells = [c.text for t in doc.tables for row in t.rows for c in row.cells]
        assert "Goal" in cells and "Met" in cells
        assert not any("|" in p.text for p in doc.paragraphs)
        assert [p.text for p in doc.paragraphs if p.style.name == "List Bullet"] == ["Risk of regression", "Core deficits"]
