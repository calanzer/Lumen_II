"""Tests for the period, narrative, export, template and client-detail endpoints."""

import io
import json
import threading
import time
import zipfile
from pathlib import Path

import pytest

from schemas.narrative import CustomNarrative, KeyedSection

FIXTURES = Path(__file__).parent / "fixtures"


def login(client):
    return client.post("/api/auth/login", json={"username": "tester", "password": "pw-123"})


def imported(app) -> dict:
    """Sign in, import the stubbed report, and return the import result (client + period ids)."""
    login(app)
    job = app.post("/api/imports", files={"file": ("r.docx", b"x", "application/octet-stream")}).json()
    deadline = time.time() + 5
    while time.time() < deadline:
        job = app.get(f"/api/imports/{job['id']}").json()
        if job["stage"] in ("done", "error"):
            break
        time.sleep(0.02)
    assert job["stage"] == "done", job
    return job["result"]


def wait_generation(app, period_id, *stages, timeout=5.0):
    deadline = time.time() + timeout
    status = {}
    while time.time() < deadline:
        status = app.get(f"/api/periods/{period_id}/generate").json()
        if status["stage"] in stages:
            return status
        time.sleep(0.02)
    raise AssertionError(f"generation never reached {stages}; last: {status}")


def custom_narrative(payor_key="aetna") -> CustomNarrative:
    return CustomNarrative(
        payor_key=payor_key,
        template_name="Our Aetna layout",
        sections=[
            KeyedSection(key="intro", section_name="Introduction", content="Hello", source_data_keys=["client"]),
            KeyedSection(key="plan", section_name="Plan", content="Continue", source_data_keys=["nope"]),
        ],
        overall_confidence=0.9,
    )


class TestPeriodAccess:
    def test_every_period_and_template_route_requires_login(self, app):
        assert app.get("/api/periods/x").status_code == 401
        assert app.patch("/api/periods/x", json={"notes": ""}).status_code == 401
        assert app.put("/api/periods/x/data", json={}).status_code == 401
        assert app.put("/api/periods/x/narrative", json={"sections": []}).status_code == 401
        assert app.post("/api/periods/x/generate").status_code == 401
        assert app.get("/api/periods/x/generate").status_code == 401
        assert app.post("/api/periods/x/export", json={"confirmed": True}).status_code == 401
        assert app.post("/api/periods/x/submitted").status_code == 401
        assert app.get("/api/templates/aetna").status_code == 401
        assert app.put("/api/templates/aetna", json={"name": "n", "sections": []}).status_code == 401
        assert app.delete("/api/templates/aetna").status_code == 401
        assert app.post("/api/templates/analyze", files={"file": ("r.pdf", b"x")}).status_code == 401
        assert app.post("/api/clients/x/periods", json={}).status_code == 401

    def test_unknown_periods_are_not_found(self, app):
        login(app)
        assert app.get("/api/periods/nope").status_code == 404
        assert app.put("/api/periods/nope/data", json={}).status_code == 404
        assert app.post("/api/periods/nope/generate").status_code == 404
        assert app.post("/api/periods/nope/export", json={"confirmed": True}).status_code == 404


class TestPeriodDetail:
    def test_it_returns_everything_the_screens_need(self, app):
        result = imported(app)
        body = app.get(f"/api/periods/{result['period_id']}").json()

        assert body["client"]["display_name"] and body["client"]["payor"] == "aetna"
        assert body["client"]["payor_name"] == "Aetna"
        assert body["data"]["client"]["client_id"] == "HB-100"
        assert 0 <= body["validation"]["score"] <= 1
        assert body["comparison"] is None and body["template"] is None

        narrative = body["narrative"]
        assert narrative["kind"] == "default" and len(narrative["sections"]) == 9
        assert narrative["stale"] is False
        first = narrative["sections"][0]
        assert {"key", "title", "content", "requires_review", "review_note", "source"} <= set(first)
        assert "client" in first["source"]  # the data behind the section, for side-by-side review

    def test_a_period_without_a_report_has_no_data_or_narrative(self, app):
        result = imported(app)
        login(app)
        new = app.post(f"/api/clients/{result['client_id']}/periods", json={"period_start": "2027-01-01", "period_end": "2027-06-30"}).json()
        body = app.get(f"/api/periods/{new['id']}").json()
        assert body["data"] is None and body["narrative"] is None and body["validation"] is None

    def test_the_active_template_is_reported(self, app):
        from data.store import save_template
        from pipeline.template_extractor import sections_from_rows

        result = imported(app)
        save_template("aetna", "Ours", sections_from_rows([{"title": "A"}, {"title": "B"}]))
        body = app.get(f"/api/periods/{result['period_id']}").json()
        assert body["template"] == {"name": "Ours", "section_count": 2}

    def test_a_custom_narrative_shows_the_fields_it_listed_as_its_source(self, app):
        from data.store import save_narrative

        result = imported(app)
        save_narrative(result["period_id"], custom_narrative())
        narrative = app.get(f"/api/periods/{result['period_id']}").json()["narrative"]
        assert narrative["kind"] == "custom" and narrative["template_name"] == "Our Aetna layout"
        intro, plan = narrative["sections"]
        assert list(intro["source"]) == ["client"]
        assert plan["source"] == {}  # a field that doesn't exist is simply not shown


class TestComparison:
    def test_progress_since_the_prior_authorization(self, app):
        from data.store import create_auth_period, save_extraction
        from schemas.clinical_data import ExtractedClinicalData

        result = imported(app)
        current = app.get(f"/api/periods/{result['period_id']}").json()["data"]

        before = json.loads(json.dumps(current))
        before["skill_acquisition_targets"][0]["is_mastered"] = False
        # Aggression was 2.7 now; make it 5.4 before so it halved
        target = next(b for b in before["behavior_reduction_targets"] if b["behavior_name"] == "Aggression")
        target["current_value"] = 5.4
        prior_id = create_auth_period(result["client_id"], "2025-01-01", "2025-06-30")
        save_extraction(prior_id, ExtractedClinicalData.model_validate(before), "old.docx", {"score": 1, "missing": [], "warnings": []})

        comparison = app.get(f"/api/periods/{result['period_id']}").json()["comparison"]
        assert comparison["prior_start"] == "2025-01-01"
        assert comparison["skills_mastered"] - comparison["skills_mastered_prior"] >= 0
        aggression = next(c for c in comparison["behavior_changes"] if c["name"] == "Aggression")
        assert aggression["prior"] == 5.4 and aggression["current"] == 2.7
        assert aggression["percent_change"] == pytest.approx(-50.0)

    def test_no_prior_data_means_no_comparison(self, app):
        from data.store import create_auth_period

        result = imported(app)
        create_auth_period(result["client_id"], "2025-01-01", "2025-06-30")  # empty prior period
        assert app.get(f"/api/periods/{result['period_id']}").json()["comparison"] is None


class TestNotes:
    def test_notes_are_saved_and_come_back(self, app):
        result = imported(app)
        url = f"/api/periods/{result['period_id']}"
        assert app.patch(url, json={"notes": "Call mom re: schedule"}).status_code == 200
        assert app.get(url).json()["notes"] == "Call mom re: schedule"
        app.patch(url, json={"notes": ""})
        assert app.get(url).json()["notes"] == ""

    def test_absurdly_long_notes_are_refused(self, app):
        result = imported(app)
        assert app.patch(f"/api/periods/{result['period_id']}", json={"notes": "x" * 6000}).status_code == 422


class TestSavingData:
    def test_edits_are_saved_and_validation_is_recomputed(self, app):
        result = imported(app)
        url = f"/api/periods/{result['period_id']}"
        data = app.get(url).json()["data"]
        data["client"]["supervising_bcba"] = "Dr. New Name"
        data["clinical_justification_for_hours"] = None

        reply = app.put(f"{url}/data", json=data)

        assert reply.status_code == 200
        assert reply.json()["data"]["client"]["supervising_bcba"] == "Dr. New Name"
        assert "score" in reply.json()["validation"]
        assert app.get(url).json()["data"]["client"]["supervising_bcba"] == "Dr. New Name"

    def test_a_value_the_bcba_left_blank_stays_blank_not_zero(self, app):
        result = imported(app)
        url = f"/api/periods/{result['period_id']}"
        data = app.get(url).json()["data"]
        data["client"]["age_years"] = None
        data["skill_acquisition_targets"][0]["current_accuracy_pct"] = None

        app.put(f"{url}/data", json=data)

        saved = app.get(url).json()["data"]
        assert saved["client"]["age_years"] is None
        assert saved["skill_acquisition_targets"][0]["current_accuracy_pct"] is None

    def test_an_invalid_value_is_refused_with_a_reason_and_nothing_changes(self, app):
        result = imported(app)
        url = f"/api/periods/{result['period_id']}"
        before = app.get(url).json()["data"]
        bad = json.loads(json.dumps(before))
        bad["skill_acquisition_targets"][0]["current_accuracy_pct"] = 150

        reply = app.put(f"{url}/data", json=bad)

        assert reply.status_code == 422
        assert "current_accuracy_pct" in reply.json()["detail"]
        assert app.get(url).json()["data"] == before

    def test_garbage_is_refused(self, app):
        result = imported(app)
        assert app.put(f"/api/periods/{result['period_id']}/data", json={"client": 5}).status_code == 422

    def test_a_period_without_a_report_cannot_be_given_data(self, app):
        result = imported(app)
        new = app.post(f"/api/clients/{result['client_id']}/periods", json={"period_start": "2027-01-01", "period_end": "2027-06-30"}).json()
        data = app.get(f"/api/periods/{result['period_id']}").json()["data"]
        assert app.put(f"/api/periods/{new['id']}/data", json=data).status_code == 409

    def test_editing_data_makes_the_draft_stale(self, app):
        result = imported(app)
        url = f"/api/periods/{result['period_id']}"
        data = app.get(url).json()["data"]
        data["client"]["supervising_bcba"] = "Someone Else"

        reply = app.put(f"{url}/data", json=data).json()

        assert reply["narrative_stale"] is True
        assert app.get(url).json()["narrative"]["stale"] is True


class TestEditingTheNarrative:
    def test_section_edits_are_saved_and_nothing_else_changes(self, app):
        result = imported(app)
        url = f"/api/periods/{result['period_id']}"
        before = app.get(url).json()["narrative"]["sections"]

        reply = app.put(f"{url}/narrative", json={"sections": [{"key": before[2]["key"], "content": "My own words."}]})

        assert reply.status_code == 200
        after = app.get(url).json()["narrative"]["sections"]
        assert after[2]["content"] == "My own words."
        assert [s["content"] for i, s in enumerate(after) if i != 2] == [s["content"] for i, s in enumerate(before) if i != 2]

    def test_an_unknown_section_is_refused_and_nothing_is_saved(self, app):
        result = imported(app)
        url = f"/api/periods/{result['period_id']}"
        before = app.get(url).json()["narrative"]["sections"]
        keys = [before[0]["key"], "no_such_section"]

        reply = app.put(f"{url}/narrative", json={"sections": [{"key": k, "content": "changed"} for k in keys]})

        assert reply.status_code == 422
        assert app.get(url).json()["narrative"]["sections"] == before

    def test_editing_does_not_make_the_draft_stale(self, app):
        result = imported(app)
        url = f"/api/periods/{result['period_id']}"
        key = app.get(url).json()["narrative"]["sections"][0]["key"]
        app.put(f"{url}/narrative", json={"sections": [{"key": key, "content": "x"}]})
        assert app.get(url).json()["narrative"]["stale"] is False

    def test_custom_narratives_can_be_edited_too(self, app):
        from data.store import save_narrative

        result = imported(app)
        save_narrative(result["period_id"], custom_narrative())
        url = f"/api/periods/{result['period_id']}"
        app.put(f"{url}/narrative", json={"sections": [{"key": "plan", "content": "Revised plan"}]})
        assert [s["content"] for s in app.get(url).json()["narrative"]["sections"]] == ["Hello", "Revised plan"]

    def test_a_period_without_a_narrative_cannot_be_edited(self, app):
        result = imported(app)
        new = app.post(f"/api/clients/{result['client_id']}/periods", json={"period_start": "2027-01-01", "period_end": "2027-06-30"}).json()
        assert app.put(f"/api/periods/{new['id']}/narrative", json={"sections": []}).status_code == 409


class TestGeneration:
    def test_nothing_has_been_started_until_it_is(self, app):
        result = imported(app)
        assert app.get(f"/api/periods/{result['period_id']}/generate").json()["stage"] == "idle"

    def test_it_writes_a_fresh_draft_saves_it_and_reports_the_check(self, app):
        result = imported(app)
        pid = result["period_id"]
        url = f"/api/periods/{pid}"
        key = app.get(url).json()["narrative"]["sections"][0]["key"]
        app.put(f"{url}/narrative", json={"sections": [{"key": key, "content": "edited by hand"}]})

        assert app.post(f"{url}/generate").status_code == 202
        status = wait_generation(app, pid, "done", "error")

        assert status["stage"] == "done" and status["error"] is None
        assert status["discrepancies"] and status["check_error"] is None
        # the stub returns the fixture draft again, replacing the hand edit
        assert app.get(url).json()["narrative"]["sections"][0]["content"] != "edited by hand"

    def test_a_failed_draft_keeps_the_previous_narrative_and_says_why(self, app):
        result = imported(app)
        pid = result["period_id"]
        url = f"/api/periods/{pid}"
        before = app.get(url).json()["narrative"]
        app.state["fail_draft"] = "model overloaded"

        app.post(f"{url}/generate")
        status = wait_generation(app, pid, "done", "error")

        assert status["stage"] == "error" and "model overloaded" in status["error"]
        assert app.get(url).json()["narrative"] == before

    def test_a_failed_check_is_reported_not_hidden(self, app):
        result = imported(app)
        pid = result["period_id"]
        app.state["fail_check"] = "check broke"

        app.post(f"/api/periods/{pid}/generate")
        status = wait_generation(app, pid, "done", "error")

        assert status["stage"] == "done" and status["discrepancies"] is None
        assert "check broke" in status["check_error"]

    def test_a_second_request_while_one_is_running_is_refused(self, app, monkeypatch):
        import api.imports as imports

        result = imported(app)
        pid = result["period_id"]
        gate = threading.Event()
        original = imports.hooks.draft

        def slow_draft(data, payor_key):
            gate.wait(5)
            return original(data, payor_key)

        monkeypatch.setattr(imports.hooks, "draft", slow_draft)
        assert app.post(f"/api/periods/{pid}/generate").status_code == 202
        assert app.post(f"/api/periods/{pid}/generate").status_code == 409
        gate.set()
        wait_generation(app, pid, "done", "error")
        assert app.post(f"/api/periods/{pid}/generate").status_code == 202  # fine again afterwards
        wait_generation(app, pid, "done", "error")

    def test_generating_clears_the_stale_flag(self, app):
        result = imported(app)
        pid = result["period_id"]
        url = f"/api/periods/{pid}"
        data = app.get(url).json()["data"]
        data["client"]["supervising_bcba"] = "Changed"
        app.put(f"{url}/data", json=data)
        assert app.get(url).json()["narrative"]["stale"] is True

        app.post(f"{url}/generate")
        wait_generation(app, pid, "done", "error")
        assert app.get(url).json()["narrative"]["stale"] is False

    def test_a_period_without_data_cannot_be_generated(self, app):
        result = imported(app)
        new = app.post(f"/api/clients/{result['client_id']}/periods", json={"period_start": "2027-01-01", "period_end": "2027-06-30"}).json()
        assert app.post(f"/api/periods/{new['id']}/generate").status_code == 409


def docx_text(content: bytes) -> str:
    with zipfile.ZipFile(io.BytesIO(content)) as z:
        return z.read("word/document.xml").decode()


class TestExport:
    def test_it_will_not_export_without_the_confirmation(self, app):
        result = imported(app)
        pid = result["period_id"]
        for body in ({}, {"confirmed": False}):
            assert app.post(f"/api/periods/{pid}/export", json=body).status_code == 422
        assert app.get(f"/api/periods/{pid}").json()["exported_at"] is None

    def test_a_confirmed_export_downloads_a_word_file_and_marks_the_period(self, app):
        result = imported(app)
        pid = result["period_id"]

        reply = app.post(f"/api/periods/{pid}/export", json={"confirmed": True})

        assert reply.status_code == 200
        assert reply.content[:2] == b"PK"  # a .docx is a zip
        assert reply.headers["content-type"].startswith("application/vnd.openxmlformats")
        assert reply.headers["content-disposition"] == 'attachment; filename="reauth_aetna_HB-100_2026-06-30.docx"'
        period = app.get(f"/api/periods/{pid}").json()
        assert period["status"] == "exported" and period["exported_at"]

    def test_the_document_contains_the_edited_text(self, app):
        result = imported(app)
        pid = result["period_id"]
        url = f"/api/periods/{pid}"
        key = app.get(url).json()["narrative"]["sections"][0]["key"]
        app.put(f"{url}/narrative", json={"sections": [{"key": key, "content": "Quokka-approved sentence."}]})

        reply = app.post(f"{url}/export", json={"confirmed": True})

        assert "Quokka-approved sentence." in docx_text(reply.content)

    def test_the_payor_can_be_chosen_for_built_in_narratives(self, app):
        result = imported(app)
        reply = app.post(f"/api/periods/{result['period_id']}/export", json={"confirmed": True, "payor_key": "optum"})
        assert 'filename="reauth_optum_' in reply.headers["content-disposition"]

    def test_an_unknown_payor_is_refused(self, app):
        result = imported(app)
        reply = app.post(f"/api/periods/{result['period_id']}/export", json={"confirmed": True, "payor_key": "nope"})
        assert reply.status_code == 422
        assert app.get(f"/api/periods/{result['period_id']}").json()["exported_at"] is None

    def test_a_template_driven_narrative_ignores_a_different_payor_choice(self, app):
        from data.store import save_narrative

        result = imported(app)
        save_narrative(result["period_id"], custom_narrative("aetna"))
        reply = app.post(f"/api/periods/{result['period_id']}/export", json={"confirmed": True, "payor_key": "optum"})
        assert reply.status_code == 200 and 'filename="reauth_aetna_' in reply.headers["content-disposition"]

    def test_filenames_cannot_be_used_to_inject_headers(self, app):
        result = imported(app)
        pid = result["period_id"]
        url = f"/api/periods/{pid}"
        data = app.get(url).json()["data"]
        data["client"]["client_id"] = 'HB"; x=1\r\nSet-Cookie: a=b'
        app.put(f"{url}/data", json=data)

        reply = app.post(f"{url}/export", json={"confirmed": True})

        disposition = reply.headers["content-disposition"]
        assert "\r" not in disposition and "\n" not in disposition and disposition.count('"') == 2
        assert "set-cookie" not in reply.headers

    def test_a_period_without_a_narrative_cannot_be_exported(self, app):
        result = imported(app)
        new = app.post(f"/api/clients/{result['client_id']}/periods", json={"period_start": "2027-01-01", "period_end": "2027-06-30"}).json()
        assert app.post(f"/api/periods/{new['id']}/export", json={"confirmed": True}).status_code == 409

    def test_it_is_submitted_only_after_it_has_been_exported(self, app):
        result = imported(app)
        pid = result["period_id"]
        assert app.post(f"/api/periods/{pid}/submitted").status_code == 409
        app.post(f"/api/periods/{pid}/export", json={"confirmed": True})
        assert app.post(f"/api/periods/{pid}/submitted").status_code == 200
        assert app.get(f"/api/periods/{pid}").json()["status"] == "submitted"


class TestNewPeriods:
    def test_a_period_can_be_added_to_a_client(self, app):
        result = imported(app)
        reply = app.post(f"/api/clients/{result['client_id']}/periods", json={"period_start": "2027-01-01", "period_end": "2027-06-30"})
        assert reply.status_code == 201
        assert reply.json()["status"] == "draft" and reply.json()["has_data"] is False
        detail = app.get(f"/api/clients/{result['client_id']}").json()
        assert detail["period_count"] == 2

    @pytest.mark.parametrize(
        "body",
        [
            {"period_start": "2027-06-30", "period_end": "2027-01-01"},
            {"period_start": "2027-01-01", "period_end": "2027-01-01"},
            {"period_start": "not a date", "period_end": "2027-01-01"},
            {},
        ],
    )
    def test_bad_dates_are_refused(self, app, body):
        result = imported(app)
        assert app.post(f"/api/clients/{result['client_id']}/periods", json=body).status_code == 422

    def test_archived_or_unknown_clients_have_no_new_periods(self, app):
        login(app)
        assert app.post("/api/clients/nope/periods", json={"period_start": "2027-01-01", "period_end": "2027-06-30"}).status_code == 404


class TestClientDetailExtras:
    def test_periods_carry_the_summary_the_details_screen_shows(self, app):
        result = imported(app)
        app.patch(f"/api/periods/{result['period_id']}", json={"notes": "n1"})
        period = app.get(f"/api/clients/{result['client_id']}").json()["periods"][0]

        assert period["notes"] == "n1" and period["extracted_at"]
        assert period["validation"]["score"] > 0 and isinstance(period["validation"]["missing"], int)
        assert period["counts"]["skill_targets"] == 10 and period["counts"]["assessments"] == 3
        assert period["narrative"]["confidence"] > 0 and isinstance(period["narrative"]["flags"], int)

    def test_an_empty_period_has_no_summary(self, app):
        result = imported(app)
        app.post(f"/api/clients/{result['client_id']}/periods", json={"period_start": "2027-01-01", "period_end": "2027-06-30"})
        newest = app.get(f"/api/clients/{result['client_id']}").json()["periods"][0]
        assert newest["validation"] is None and newest["counts"] is None and newest["narrative"] is None

    def test_trends_need_two_periods_with_vbmapp_scores(self, app):
        from data.store import create_auth_period, save_extraction
        from schemas.clinical_data import ExtractedClinicalData

        result = imported(app)
        assert app.get(f"/api/clients/{result['client_id']}").json()["trends"] is None

        older = app.get(f"/api/periods/{result['period_id']}").json()["data"]
        older["assessments"][0]["domain_scores"] = {"Mand": 3.0, "Tact": 2.0}
        pid = create_auth_period(result["client_id"], "2025-01-01", "2025-06-30")
        save_extraction(pid, ExtractedClinicalData.model_validate(older), "old.docx")

        trends = app.get(f"/api/clients/{result['client_id']}").json()["trends"]
        assert trends["columns"] == ["2025-01", "2026-01"]  # oldest first
        mand = next(r for r in trends["rows"] if r["domain"] == "Mand")
        assert mand["values"][0] == 3.0 and len(mand["values"]) == 2


class TestTemplateLibrary:
    def stub(self, monkeypatch, raise_error=None):
        import api.templates as templates
        from pipeline.template_extractor import sections_from_rows

        def analyze(content, name):
            if raise_error:
                raise RuntimeError(raise_error)
            return {"sections": sections_from_rows([{"title": "Summary", "guidance": "Overview"}, {"title": "Plan"}]), "style_notes": "Formal."}

        monkeypatch.setattr(templates.hooks, "analyze", analyze)

    def test_a_payor_starts_on_the_built_in_layout(self, app):
        login(app)
        body = app.get("/api/templates/aetna").json()
        assert body["active"] is None and body["payor_name"] == "Aetna"
        assert body["default_sections"][0] == "Client Overview" and len(body["default_sections"]) == 9

    def test_unknown_payors_are_not_found(self, app):
        login(app)
        assert app.get("/api/templates/nope").status_code == 404
        assert app.put("/api/templates/nope", json={"name": "n", "sections": []}).status_code == 404
        assert app.delete("/api/templates/nope").status_code == 404

    def test_a_past_report_is_analyzed_into_editable_sections(self, app, monkeypatch):
        self.stub(monkeypatch)
        login(app)
        reply = app.post("/api/templates/analyze", files={"file": ("old report.pdf", b"x")})
        assert reply.status_code == 200
        assert reply.json() == {
            "source_filename": "old report.pdf",
            "style_notes": "Formal.",
            "sections": [{"title": "Summary", "guidance": "Overview"}, {"title": "Plan", "guidance": ""}],
        }
        # analyzing saves nothing
        assert app.get("/api/templates/aetna").json()["active"] is None

    def test_analysis_refuses_other_file_types_and_empty_files(self, app, monkeypatch):
        self.stub(monkeypatch)
        login(app)
        assert app.post("/api/templates/analyze", files={"file": ("r.txt", b"x")}).status_code == 415
        assert app.post("/api/templates/analyze", files={"file": ("r.pdf", b"")}).status_code == 400

    def test_a_failed_analysis_says_why(self, app, monkeypatch):
        self.stub(monkeypatch, raise_error="no sections found")
        login(app)
        reply = app.post("/api/templates/analyze", files={"file": ("r.pdf", b"x")})
        assert reply.status_code == 422 and "no sections found" in reply.json()["detail"]

    def test_a_reviewed_template_is_saved_and_becomes_active(self, app):
        login(app)
        body = {
            "name": "  Aetna — our report  ",
            "style_notes": " Formal. ",
            "source_filename": "old.pdf",
            "sections": [{"title": "Plan", "guidance": "Next steps"}, {"title": " "}, {"title": "Summary"}],
        }
        reply = app.put("/api/templates/aetna", json=body)

        assert reply.status_code == 200
        active = reply.json()["active"]
        assert active["name"] == "Aetna — our report" and active["style_notes"] == "Formal."
        assert [s["title"] for s in active["sections"]] == ["Plan", "Summary"]  # order kept, blanks dropped
        assert app.get("/api/templates/aetna").json()["active"] == active
        flagged = {p["key"]: p["has_custom_template"] for p in app.get("/api/payors").json()}
        assert flagged["aetna"] is True and flagged["optum"] is False

    @pytest.mark.parametrize(
        "body,fragment",
        [
            ({"name": "n", "sections": [{"title": "Only one"}]}, "two sections"),
            ({"name": "n", "sections": [{"title": "A"}, {"title": ""}]}, "two sections"),
            ({"name": "  ", "sections": [{"title": "A"}, {"title": "B"}]}, "name"),
        ],
    )
    def test_incomplete_templates_are_refused(self, app, body, fragment):
        login(app)
        reply = app.put("/api/templates/aetna", json=body)
        assert reply.status_code == 422 and fragment in reply.json()["detail"]
        assert app.get("/api/templates/aetna").json()["active"] is None

    def test_going_back_to_the_default_clears_the_active_template(self, app):
        login(app)
        app.put("/api/templates/aetna", json={"name": "n", "sections": [{"title": "A"}, {"title": "B"}]})
        reply = app.delete("/api/templates/aetna")
        assert reply.status_code == 200 and reply.json()["active"] is None
        assert app.get("/api/templates/aetna").json()["active"] is None

    def test_templates_are_per_payor(self, app):
        login(app)
        app.put("/api/templates/aetna", json={"name": "n", "sections": [{"title": "A"}, {"title": "B"}]})
        assert app.get("/api/templates/optum").json()["active"] is None
