"""Tests for turning a dropped report into a client, period and draft."""

import json
import os
from datetime import date
from pathlib import Path

import pytest

from pipeline import intake
from pipeline.exporter import PAYOR_TEMPLATES
from schemas.clinical_data import ExtractedClinicalData
from schemas.narrative import TemplateSection

FIXTURES = Path(__file__).parent / "fixtures"
TEST_DB_PATH = FIXTURES / "test_intake.db"


@pytest.fixture(autouse=True)
def clean_db(monkeypatch):
    monkeypatch.setattr("data.store.DB_PATH", TEST_DB_PATH)
    from data.store import init_db

    init_db()
    yield
    for suffix in ("", "-wal", "-shm"):
        extra = Path(str(TEST_DB_PATH) + suffix)
        if extra.exists():
            os.remove(extra)


def make_data(**client_fields) -> ExtractedClinicalData:
    with open(FIXTURES / "realistic_extraction.json") as f:
        raw = json.load(f)
    raw["client"].update(
        {
            "client_id": "HB-100",
            "payor_name": "Aetna",
            "auth_period_start": "2026-01-01",
            "auth_period_end": "2026-06-30",
            "report_period_start": None,
            "report_period_end": None,
        }
    )
    raw["client"].update(client_fields)
    return ExtractedClinicalData.model_validate(raw)


VALIDATION = {"is_complete": True, "score": 1.0, "missing": [], "warnings": []}


class TestDetectPayor:
    @pytest.mark.parametrize(
        "text, key",
        [
            ("Aetna", "aetna"),
            ("AETNA Better Health", "aetna"),
            ("Anthem Blue Cross California", "anthem_blue_cross_ca"),
            ("Elevance Health", "anthem_blue_cross_ca"),
            ("Optum / UnitedHealthcare", "optum"),
            ("United Healthcare", "optum"),
            ("Blue Shield of California", "blue_shield_ca"),
            ("Medi-Cal Managed Care", "medi_cal"),
        ],
    )
    def test_recognizes_payors(self, text, key):
        assert intake.detect_payor_key(text) == key

    @pytest.mark.parametrize("text", [None, "", "Cigna", "Self pay"])
    def test_unknown_is_none(self, text):
        assert intake.detect_payor_key(text) is None

    def test_every_alias_key_is_a_real_payor(self):
        assert set(intake.PAYOR_ALIASES) <= set(PAYOR_TEMPLATES)


class TestFindClient:
    clients = [
        {"id": "1", "client_identifier": "HB-2025-0311", "display_name": "Sam W."},
        {"id": "2", "client_identifier": None, "display_name": "CR-77"},
    ]

    def test_matches_ignoring_case_and_punctuation(self):
        assert intake.find_client(self.clients, "hb 2025 0311")["id"] == "1"

    def test_matches_display_name_when_no_identifier(self):
        assert intake.find_client(self.clients, "cr77")["id"] == "2"

    def test_no_match_or_no_id(self):
        assert intake.find_client(self.clients, "HB-999") is None
        assert intake.find_client(self.clients, None) is None
        assert intake.find_client(self.clients, "  ") is None


class TestBuildPlan:
    def test_new_client_everything_readable_asks_nothing(self):
        plan = intake.build_plan(make_data(), clients=[])
        assert plan.questions == []
        assert plan.client is None and plan.client_identifier == "HB-100"
        assert plan.payor_key == "aetna"
        assert (plan.period_start, plan.period_end) == (date(2026, 1, 1), date(2026, 6, 30))

    def test_existing_client_keeps_their_payor_over_the_report(self):
        clients = [{"id": "9", "client_identifier": "HB-100", "display_name": "x", "payor": "optum"}]
        plan = intake.build_plan(make_data(payor_name="Aetna"), clients)
        assert plan.client["id"] == "9" and plan.payor_key == "optum" and plan.questions == []

    def test_unreadable_payor_for_new_client_is_asked(self):
        assert intake.ASK_PAYOR in intake.build_plan(make_data(payor_name=None), []).questions
        assert intake.ASK_PAYOR in intake.build_plan(make_data(payor_name="Cigna"), []).questions

    def test_unreadable_payor_not_asked_for_existing_client(self):
        clients = [{"id": "9", "client_identifier": "HB-100", "display_name": "x", "payor": "optum"}]
        assert intake.build_plan(make_data(payor_name=None), clients).questions == []

    def test_missing_client_id_is_asked(self):
        assert intake.ASK_CLIENT in intake.build_plan(make_data(client_id=None), []).questions

    def test_report_period_stands_in_for_missing_authorization_period(self):
        plan = intake.build_plan(
            make_data(
                auth_period_start=None,
                auth_period_end=None,
                report_period_start="2025-07-01",
                report_period_end="2025-12-31",
            ),
            [],
        )
        assert plan.questions == []
        assert (plan.period_start, plan.period_end) == (date(2025, 7, 1), date(2025, 12, 31))
        assert any("doesn't state an authorization period" in n for n in plan.notes)

    def test_no_dates_at_all_is_asked(self):
        plan = intake.build_plan(make_data(auth_period_start=None, auth_period_end=None), [])
        assert intake.ASK_PERIOD in plan.questions


class TestApplyImport:
    def test_creates_client_period_and_saves_extraction(self):
        from data.store import get_auth_period, get_client

        data = make_data()
        result = intake.apply_import(intake.build_plan(data, []), data, "r.pdf", VALIDATION)

        assert result.client_created and not result.period_reused
        client = get_client(result.client_id)
        assert client["client_identifier"] == "HB-100" and client["payor"] == "aetna"
        assert client["diagnosis_codes"] == list(data.client.diagnosis_codes)
        period = get_auth_period(result.period_id)
        assert (period["period_start"], period["period_end"]) == ("2026-01-01", "2026-06-30")
        assert period["extracted_data_parsed"].client.client_id == "HB-100"
        assert period["uploaded_filename"] == "r.pdf"

    def test_second_report_for_same_client_reuses_client_and_period(self):
        from data.store import list_auth_periods, list_clients

        data = make_data()
        first = intake.apply_import(intake.build_plan(data, []), data, "a.pdf", VALIDATION)
        second = intake.apply_import(intake.build_plan(data, list_clients()), data, "b.pdf", VALIDATION)

        assert not second.client_created and second.period_reused
        assert second.client_id == first.client_id and second.period_id == first.period_id
        assert len(list_clients()) == 1 and len(list_auth_periods(first.client_id)) == 1

    def test_new_period_for_known_client(self):
        from data.store import list_auth_periods, list_clients

        first = intake.apply_import(intake.build_plan(make_data(), []), make_data(), "a.pdf", VALIDATION)
        later = make_data(auth_period_start="2026-07-01", auth_period_end="2026-12-31")
        second = intake.apply_import(intake.build_plan(later, list_clients()), later, "b.pdf", VALIDATION)

        assert second.client_id == first.client_id and second.period_id != first.period_id
        assert len(list_auth_periods(first.client_id)) == 2

    def test_answers_fill_in_what_the_report_lacked(self):
        from data.store import get_client

        data = make_data(client_id=None, payor_name=None, auth_period_start=None, auth_period_end=None)
        plan = intake.build_plan(data, [])
        assert set(plan.questions) == {intake.ASK_CLIENT, intake.ASK_PAYOR, intake.ASK_PERIOD}

        result = intake.apply_import(
            plan,
            data,
            "r.pdf",
            VALIDATION,
            intake.Answers(
                new_identifier="HB-NEW",
                payor_key="optum",
                period_start=date(2026, 3, 1),
                period_end=date(2026, 8, 31),
            ),
        )
        client = get_client(result.client_id)
        assert client["client_identifier"] == "HB-NEW" and client["payor"] == "optum"

    def test_choosing_an_existing_client_for_a_report_without_an_id(self):
        from data.store import create_client, list_clients

        existing = create_client(display_name="Pat", payor="aetna")
        data = make_data(client_id=None)
        result = intake.apply_import(
            intake.build_plan(data, list_clients()), data, "r.pdf", VALIDATION, intake.Answers(existing_client_id=existing)
        )
        assert result.client_id == existing and not result.client_created

    def test_missing_answers_raise_instead_of_guessing(self):
        data = make_data(payor_name=None)
        with pytest.raises(ValueError, match="payor"):
            intake.apply_import(intake.build_plan(data, []), data, "r.pdf", VALIDATION)
        data = make_data(auth_period_start=None, auth_period_end=None)
        with pytest.raises(ValueError, match="period"):
            intake.apply_import(intake.build_plan(data, []), data, "r.pdf", VALIDATION)


class TestAnswersReachTheData:
    """What the BCBA tells us must be in the saved data, not just in the records."""

    def _import_with_answers(self, **client_fields):
        data = make_data(client_id=None, payor_name=None, auth_period_start=None, auth_period_end=None, **client_fields)
        answers = intake.Answers(
            new_identifier="HB-NEW",
            payor_key="optum",
            period_start=date(2026, 3, 1),
            period_end=date(2026, 8, 31),
        )
        result = intake.apply_import(intake.build_plan(data, []), data, "r.pdf", VALIDATION, answers)
        return data, result

    def test_answers_fill_the_clients_fields(self):
        original, result = self._import_with_answers()
        info = result.data.client
        assert info.client_id == "HB-NEW"
        assert info.payor_name == "Optum / UnitedHealthcare"
        assert (info.auth_period_start, info.auth_period_end) == (date(2026, 3, 1), date(2026, 8, 31))
        assert original.client.client_id is None  # the caller's object is left alone

    def test_validation_is_recomputed_so_answered_fields_are_no_longer_missing(self):
        _, result = self._import_with_answers()
        missing = [m["field"] for m in result.validation["missing"]]
        assert "auth_period_start" not in missing and "auth_period_end" not in missing

    def test_saved_data_includes_the_answers(self):
        from data.store import get_auth_period

        _, result = self._import_with_answers()
        saved = get_auth_period(result.period_id)["extracted_data_parsed"]
        assert saved.client.client_id == "HB-NEW"
        assert saved.client.auth_period_start == date(2026, 3, 1)

    def test_a_period_borrowed_from_the_report_is_not_called_an_authorization_period(self):
        data = make_data(
            auth_period_start=None,
            auth_period_end=None,
            report_period_start="2025-07-01",
            report_period_end="2025-12-31",
        )
        result = intake.apply_import(intake.build_plan(data, []), data, "r.pdf", VALIDATION)
        assert result.data.client.auth_period_start is None
        missing = [m["field"] for m in result.validation["missing"]]
        assert "auth_period_start" in missing  # still flagged for the BCBA to confirm

    def test_a_matched_clients_id_fills_a_report_that_lacked_one(self):
        from data.store import create_client, list_clients

        existing = create_client(display_name="Pat", client_identifier="HB-EXISTING", payor="aetna")
        data = make_data(client_id=None)
        result = intake.apply_import(
            intake.build_plan(data, list_clients()),
            data,
            "r.pdf",
            VALIDATION,
            intake.Answers(existing_client_id=existing),
        )
        assert result.data.client.client_id == "HB-EXISTING"


class TestStaleDrafts:
    def test_hash_changes_when_data_changes(self):
        data = make_data()
        before = intake.source_hash(data)
        data.client.age_years = (data.client.age_years or 0) + 1
        assert intake.source_hash(data) != before

    def test_narrative_is_stale_only_after_the_data_changes(self):
        from schemas.narrative import CustomNarrative

        data = make_data()
        narrative = CustomNarrative(sections=[], source_hash=intake.source_hash(data))
        assert not intake.is_stale(narrative, data)
        data.client.age_years = (data.client.age_years or 0) + 1
        assert intake.is_stale(narrative, data)

    def test_narrative_without_a_hash_is_never_called_stale(self):
        from schemas.narrative import CustomNarrative

        assert not intake.is_stale(CustomNarrative(sections=[]), make_data())


class TestDraftNarrative:
    def test_uses_the_practice_template_when_there_is_one(self, monkeypatch):
        import pipeline.generator as gen
        from data.store import save_template

        save_template("aetna", "Ours", [TemplateSection(key="a", title="A"), TemplateSection(key="b", title="B")])
        calls = {}

        def fake_custom(data, template, payor_name, payor_key=""):
            calls["args"] = (template.name, payor_name, payor_key)
            return gen.assemble_custom_narrative({"sections": [{"key": "a", "content": "x"}]}, template, payor_key)

        monkeypatch.setattr(gen, "generate_custom_narrative", fake_custom)
        monkeypatch.setattr(gen, "generate_narrative", lambda d: pytest.fail("default layout used"))

        data = make_data()
        narrative = intake.draft_narrative(data, "aetna")

        assert calls["args"] == ("Ours", "Aetna", "aetna")
        assert narrative.source_hash == intake.source_hash(data)

    def test_falls_back_to_the_default_layout_naming_the_payor(self, monkeypatch):
        import pipeline.generator as gen
        from schemas.narrative import AnthemReauthNarrative

        with open(FIXTURES / "realistic_narrative.json") as f:
            default = AnthemReauthNarrative.model_validate(json.load(f))
        seen = {}

        def fake_default(data, payor_name):
            seen["payor_name"] = payor_name
            return default

        monkeypatch.setattr(gen, "generate_narrative", fake_default)
        monkeypatch.setattr(gen, "generate_custom_narrative", lambda *a, **k: pytest.fail("template used"))

        data = make_data()
        narrative = intake.draft_narrative(data, "aetna")

        assert seen["payor_name"] == "Aetna"  # not "Anthem": no template, but still this payor
        assert narrative.source_hash == intake.source_hash(data)


class TestStaleMissingNotes:
    def test_answered_fields_are_dropped_from_the_extractions_missing_list(self):
        data = make_data(client_id=None, payor_name=None, auth_period_start=None, auth_period_end=None)
        data.missing_fields = [
            "client_id",
            "auth_period_start",
            "payor_name",
            "skill_acquisition_targets[].date_introduced",
        ]
        answers = intake.Answers(
            new_identifier="HB-NEW", payor_key="optum", period_start=date(2026, 3, 1), period_end=date(2026, 8, 31)
        )
        result = intake.apply_import(intake.build_plan(data, []), data, "r.pdf", VALIDATION, answers)

        assert result.data.missing_fields == ["skill_acquisition_targets[].date_introduced"]

    def test_notes_about_other_fields_stay_even_if_the_client_has_an_id(self):
        data = make_data()
        data.missing_fields = ["assessments[].percentile", "discharge_plan.estimated_discharge_date"]
        result = intake.apply_import(intake.build_plan(data, []), data, "r.pdf", VALIDATION)
        assert result.data.missing_fields == data.missing_fields
