"""Tests for the API: login, protected routes, and the import job flow."""

import json
import os
import time
from pathlib import Path

import bcrypt
import pytest
import yaml
from fastapi.testclient import TestClient

from schemas.clinical_data import ExtractedClinicalData
from schemas.narrative import AnthemReauthNarrative

FIXTURES = Path(__file__).parent / "fixtures"
TEST_DB_PATH = FIXTURES / "test_api.db"

def login(client, username="tester", password="pw-123"):
    return client.post("/api/auth/login", json={"username": username, "password": password})


def upload(client, name="report.docx", content=b"fake report bytes"):
    return client.post("/api/imports", files={"file": (name, content, "application/octet-stream")})


def wait_for(client, job_id, *stages, timeout=5.0):
    deadline = time.time() + timeout
    while time.time() < deadline:
        job = client.get(f"/api/imports/{job_id}").json()
        if job["stage"] in stages:
            return job
        time.sleep(0.02)
    raise AssertionError(f"job never reached {stages}; last: {job}")


class TestLogin:
    def test_wrong_password_and_unknown_user_are_rejected_alike(self, app):
        assert login(app, password="nope").status_code == 401
        assert login(app, username="ghost").status_code == 401
        assert app.get("/api/auth/me").status_code == 401

    def test_login_then_me_then_logout(self, app):
        response = login(app)
        assert response.status_code == 200 and response.json()["name"] == "Test BCBA"
        assert app.get("/api/auth/me").json()["username"] == "tester"
        app.post("/api/auth/logout")
        assert app.get("/api/auth/me").status_code == 401

    def test_repeated_failures_lock_the_account_even_for_the_right_password(self, app):
        for _ in range(5):
            assert login(app, password="wrong").status_code == 401
        assert login(app).status_code == 429

    def test_a_success_clears_the_failure_count(self, app):
        for _ in range(4):
            login(app, password="wrong")
        assert login(app).status_code == 200
        app.post("/api/auth/logout")
        for _ in range(4):
            login(app, password="wrong")
        assert login(app).status_code == 200

    def test_every_data_route_requires_login(self, app):
        assert app.get("/api/payors").status_code == 401
        assert app.get("/api/clients").status_code == 401
        assert upload(app).status_code == 401
        assert app.get("/api/imports/anything").status_code == 401
        assert app.post("/api/imports/anything/answers", json={}).status_code == 401
        assert app.post("/api/clients", json={"display_name": "x", "payor": "aetna"}).status_code == 401
        assert app.get("/api/clients/some-id").status_code == 401
        assert app.post("/api/clients/some-id/archive").status_code == 401
        assert app.get("/api/health").status_code == 200  # the one open route


class TestReference:
    def test_payors_flag_custom_templates(self, app):
        from data.store import save_template
        from schemas.narrative import TemplateSection

        login(app)
        before = {p["key"]: p for p in app.get("/api/payors").json()}
        assert before["aetna"]["display_name"] == "Aetna" and not before["aetna"]["has_custom_template"]

        save_template("aetna", "Ours", [TemplateSection(key="a", title="A"), TemplateSection(key="b", title="B")])
        after = {p["key"]: p for p in app.get("/api/payors").json()}
        assert after["aetna"]["has_custom_template"] and not after["optum"]["has_custom_template"]


class TestUploadValidation:
    def test_rejects_other_file_types_and_empty_files(self, app):
        login(app)
        assert upload(app, name="notes.txt").status_code == 415
        assert upload(app, name="report.pdf", content=b"").status_code == 400

    def test_accepts_pdf_and_docx_case_insensitively(self, app):
        login(app)
        assert upload(app, name="REPORT.PDF").status_code == 202
        assert upload(app, name="r.docx").status_code == 202


class TestImportFlow:
    def test_everything_readable_runs_straight_to_done(self, app):
        login(app)
        job = wait_for(app, upload(app).json()["id"], "done", "error")

        assert job["stage"] == "done" and job["error"] is None and job["questions"] == []
        result = job["result"]
        assert result["client"]["identifier"] == "HB-100" and result["client_created"] is True
        assert result["payor"] == {"key": "aetna", "name": "Aetna"}
        assert result["period"] == {"start": "2026-01-01", "end": "2026-06-30"}
        assert result["draft"]["section_count"] == 9 and result["draft"]["used_custom_template"] is False
        assert len(result["discrepancies"]) == 1 and result["check_error"] is None
        assert 0 <= result["completeness"] <= 1

        clients = app.get("/api/clients").json()
        assert [c["client_identifier"] for c in clients] == ["HB-100"] and clients[0]["payor"] == "aetna"

    def test_a_second_report_for_the_same_client_reuses_everything(self, app):
        login(app)
        wait_for(app, upload(app).json()["id"], "done")
        second = wait_for(app, upload(app).json()["id"], "done")
        assert second["result"]["client_created"] is False
        assert len(app.get("/api/clients").json()) == 1

    def test_missing_details_pause_for_answers_then_finish(self, app):
        app.state["raw"]["client"].update(
            {"client_id": None, "payor_name": None, "auth_period_start": None, "auth_period_end": None}
        )
        login(app)
        job_id = upload(app).json()["id"]
        job = wait_for(app, job_id, "needs_answers", "error")
        assert set(job["questions"]) == {"client", "payor", "period"}

        reply = app.post(
            f"/api/imports/{job_id}/answers",
            json={
                "new_identifier": "HB-NEW",
                "payor_key": "optum",
                "period_start": "2026-03-01",
                "period_end": "2026-08-31",
            },
        )
        assert reply.status_code == 202
        done = wait_for(app, job_id, "done", "error")
        assert done["result"]["client"]["identifier"] == "HB-NEW"
        assert done["result"]["payor"]["key"] == "optum"
        assert done["result"]["period"]["start"] == "2026-03-01"
        # What the BCBA supplied is no longer reported as missing from the report
        assert not any("Authorization period" in item for item in done["result"]["missing"])

    @pytest.mark.parametrize(
        "body, fragment",
        [
            ({"payor_key": "optum", "period_start": "2026-03-01", "period_end": "2026-08-31"}, "client"),
            ({"new_identifier": "X", "period_start": "2026-03-01", "period_end": "2026-08-31"}, "payor"),
            ({"new_identifier": "X", "payor_key": "nope", "period_start": "2026-03-01", "period_end": "2026-08-31"}, "payor"),
            ({"new_identifier": "X", "payor_key": "optum"}, "period"),
            ({"new_identifier": "X", "payor_key": "optum", "period_start": "2026-08-31", "period_end": "2026-03-01"}, "end"),
            ({"existing_client_id": "no-such-client", "period_start": "2026-03-01", "period_end": "2026-08-31"}, "exist"),
        ],
    )
    def test_incomplete_or_invalid_answers_are_refused_with_a_reason(self, app, body, fragment):
        app.state["raw"]["client"].update(
            {"client_id": None, "payor_name": None, "auth_period_start": None, "auth_period_end": None}
        )
        login(app)
        job_id = upload(app).json()["id"]
        wait_for(app, job_id, "needs_answers")

        reply = app.post(f"/api/imports/{job_id}/answers", json=body)

        assert reply.status_code == 422 and fragment in reply.json()["detail"].lower()
        assert app.get(f"/api/imports/{job_id}").json()["stage"] == "needs_answers"  # still waiting

    def test_choosing_an_existing_client_needs_no_payor(self, app):
        from data.store import create_client

        existing = create_client(display_name="Pat", client_identifier="HB-EXIST", payor="aetna")
        app.state["raw"]["client"].update({"client_id": None, "payor_name": None})
        login(app)
        job_id = upload(app).json()["id"]
        wait_for(app, job_id, "needs_answers")
        assert app.post(f"/api/imports/{job_id}/answers", json={"existing_client_id": existing}).status_code == 202
        done = wait_for(app, job_id, "done", "error")
        assert done["result"]["client_created"] is False and done["result"]["client_id"] == existing

    def test_answers_are_refused_when_the_job_isnt_waiting(self, app):
        login(app)
        job_id = upload(app).json()["id"]
        wait_for(app, job_id, "done")
        assert app.post(f"/api/imports/{job_id}/answers", json={}).status_code == 409


class TestFailures:
    def test_an_unreadable_report_ends_in_a_visible_error(self, app):
        app.state["fail_extract"] = "That doesn't look like a progress report."
        login(app)
        job = wait_for(app, upload(app).json()["id"], "error", "done")
        assert job["stage"] == "error" and "progress report" in job["error"] and job["result"] is None

    def test_a_failed_draft_keeps_the_imported_data_and_says_why(self, app):
        app.state["fail_draft"] = "model overloaded"
        login(app)
        job = wait_for(app, upload(app).json()["id"], "done", "error")
        assert job["stage"] == "done"
        assert job["result"]["draft"] is None and "overloaded" in job["result"]["draft_error"]
        assert len(app.get("/api/clients").json()) == 1  # the client and period were still saved

    def test_a_failed_cross_check_is_reported_not_hidden_as_zero(self, app):
        app.state["fail_check"] = "cut off"
        login(app)
        job = wait_for(app, upload(app).json()["id"], "done", "error")
        assert job["result"]["discrepancies"] is None and "cut off" in job["result"]["check_error"]
        assert job["result"]["draft"]["section_count"] == 9


class TestJobPrivacy:
    def test_another_user_cannot_see_or_answer_a_job(self, app):
        login(app)
        job_id = upload(app).json()["id"]
        wait_for(app, job_id, "done")
        app.post("/api/auth/logout")

        login(app, "other", "pw-456")
        assert app.get(f"/api/imports/{job_id}").status_code == 404
        assert app.post(f"/api/imports/{job_id}/answers", json={}).status_code == 404

    def test_the_uploaded_bytes_are_dropped_once_read(self, app):
        import api.imports as imports

        login(app)
        job_id = upload(app, content=b"sensitive bytes").json()["id"]
        wait_for(app, job_id, "done")
        assert imports.JOBS[job_id].file_bytes == b""


def new_client(app, **fields):
    body = {"display_name": "Martinez, A.", "client_identifier": "CR-2024-0847", "diagnosis_codes": ["F84.0"], "payor": "aetna"}
    body.update(fields)
    return app.post("/api/clients", json=body)


class TestClients:
    def test_an_empty_roster_is_an_empty_list(self, app):
        login(app)
        assert app.get("/api/clients").json() == []

    def test_adding_a_client_returns_it_and_it_appears_in_the_list(self, app):
        login(app)
        response = new_client(app)
        assert response.status_code == 201
        created = response.json()
        assert created["display_name"] == "Martinez, A." and created["client_identifier"] == "CR-2024-0847"
        assert created["payor"] == "aetna" and created["payor_name"] == "Aetna"
        assert created["diagnosis_codes"] == ["F84.0"] and created["period_count"] == 0 and created["latest_period"] is None
        assert [c["id"] for c in app.get("/api/clients").json()] == [created["id"]]

    def test_the_list_is_sorted_by_name(self, app):
        login(app)
        for name, ident in (("Zed", "Z-1"), ("Abe", "A-1"), ("Moe", "M-1")):
            new_client(app, display_name=name, client_identifier=ident)
        assert [c["display_name"] for c in app.get("/api/clients").json()] == ["Abe", "Moe", "Zed"]

    def test_input_is_tidied(self, app):
        login(app)
        created = new_client(
            app, display_name="  Pat  ", client_identifier="   ", diagnosis_codes=[" F84.0 ", "", "  ", "F80.2"]
        ).json()
        assert created["display_name"] == "Pat"
        assert created["client_identifier"] is None  # blank means none
        assert created["diagnosis_codes"] == ["F84.0", "F80.2"]

    @pytest.mark.parametrize(
        "fields, fragment",
        [
            ({"display_name": "   "}, "name"),
            ({"display_name": "x" * 121}, "name"),
            ({"payor": "no-such-payor"}, "payor"),
            ({"diagnosis_codes": [f"F{n}" for n in range(21)]}, "diagnosis"),
        ],
    )
    def test_invalid_clients_are_refused_with_a_reason(self, app, fields, fragment):
        login(app)
        response = new_client(app, **fields)
        assert response.status_code == 422 and fragment in response.json()["detail"].lower()
        assert app.get("/api/clients").json() == []

    def test_a_duplicate_client_id_is_refused_however_it_is_written(self, app):
        login(app)
        assert new_client(app).status_code == 201
        for variant in ("CR-2024-0847", "cr 2024 0847", "CR20240847"):
            response = new_client(app, display_name="Someone else", client_identifier=variant)
            assert response.status_code == 409 and "already exists" in response.json()["detail"], variant
        assert len(app.get("/api/clients").json()) == 1

    def test_an_id_can_be_reused_once_the_old_client_is_archived(self, app):
        login(app)
        first = new_client(app).json()
        app.post(f"/api/clients/{first['id']}/archive")
        assert new_client(app).status_code == 201

    def test_clients_without_an_id_never_clash(self, app):
        login(app)
        assert new_client(app, display_name="A", client_identifier=None).status_code == 201
        assert new_client(app, display_name="B", client_identifier=None).status_code == 201


class TestClientDetail:
    def _period(self, client_id, end_in_days, status="draft", with_data=False):
        from datetime import date, timedelta

        from data import store
        from pipeline.validator import validate_completeness

        end = date.today() + timedelta(days=end_in_days)
        period_id = store.create_auth_period(client_id, (end - timedelta(days=182)).isoformat(), end.isoformat())
        if with_data:
            with open(FIXTURES / "realistic_extraction.json") as f:
                data = ExtractedClinicalData.model_validate(json.load(f))
            store.save_extraction(period_id, data, "r.pdf", validate_completeness(data))
        if status != "draft":
            with store.get_db() as conn:
                conn.execute("UPDATE auth_periods SET status = ? WHERE id = ?", (status, period_id))
        return period_id

    def test_the_list_shows_the_authorization_to_watch(self, app):
        login(app)
        client = new_client(app).json()
        self._period(client["id"], end_in_days=-100)
        newest = self._period(client["id"], end_in_days=20, status="in_progress")
        row = app.get("/api/clients").json()[0]
        assert row["period_count"] == 2
        assert row["latest_period"]["id"] == newest
        assert row["latest_period"]["days_until_end"] == 20 and row["latest_period"]["status"] == "in_progress"

    def test_days_until_end_is_negative_once_expired(self, app):
        login(app)
        client = new_client(app).json()
        self._period(client["id"], end_in_days=-5)
        assert app.get("/api/clients").json()[0]["latest_period"]["days_until_end"] == -5

    def test_detail_lists_every_period_newest_first_without_the_heavy_data(self, app):
        login(app)
        client = new_client(app).json()
        old = self._period(client["id"], end_in_days=-100, with_data=True)
        new = self._period(client["id"], end_in_days=30)
        detail = app.get(f"/api/clients/{client['id']}").json()

        assert [p["id"] for p in detail["periods"]] == [new, old]
        assert detail["periods"][1]["has_data"] is True and detail["periods"][1]["has_narrative"] is False
        assert detail["periods"][1]["uploaded_filename"] == "r.pdf"
        assert detail["periods"][0]["has_data"] is False
        for period in detail["periods"]:
            assert "extracted_data" not in period and "narrative_data" not in period

    def test_unknown_clients_are_404(self, app):
        login(app)
        assert app.get("/api/clients/nope").status_code == 404
        assert app.post("/api/clients/nope/archive").status_code == 404

    def test_archiving_removes_the_client_from_the_roster_but_keeps_their_records(self, app):
        from data import store

        login(app)
        client = new_client(app).json()
        period = self._period(client["id"], end_in_days=10)

        assert app.post(f"/api/clients/{client['id']}/archive").json() == {"ok": True}
        assert app.get("/api/clients").json() == []
        assert app.get(f"/api/clients/{client['id']}").status_code == 404
        assert store.get_client(client["id"])["status"] == "discharged"
        assert store.get_auth_period(period) is not None  # nothing was deleted

    def test_archiving_twice_is_refused_cleanly(self, app):
        login(app)
        client = new_client(app).json()
        assert app.post(f"/api/clients/{client['id']}/archive").status_code == 200
        assert app.post(f"/api/clients/{client['id']}/archive").status_code == 404


class TestLocalSignInSkip:
    """ABA_LOCAL_NO_LOGIN=1 skips sign-in, but only for a plain same-machine browser request."""

    @pytest.fixture
    def local(self, app, monkeypatch):
        monkeypatch.setenv("ABA_LOCAL_NO_LOGIN", "1")

        def client(host="localhost", peer=("127.0.0.1", 50000)):
            return TestClient(app.app, base_url=f"http://{host}", client=peer)

        return client

    def test_off_by_default_even_on_localhost(self, app, monkeypatch):
        monkeypatch.delenv("ABA_LOCAL_NO_LOGIN", raising=False)
        c = TestClient(app.app, base_url="http://localhost", client=("127.0.0.1", 50000))
        assert c.get("/api/auth/me").status_code == 401
        assert c.get("/api/clients").status_code == 401

    def test_enabled_on_localhost_it_lets_you_straight_in(self, local):
        c = local()
        me = c.get("/api/auth/me")
        assert me.status_code == 200 and me.json() == {"username": "local", "name": "Local tester", "local": True}
        assert c.get("/api/clients").status_code == 200
        assert c.post("/api/clients", json={"display_name": "A", "payor": "aetna"}).status_code == 201

    @pytest.mark.parametrize("host", ["localhost:5173", "127.0.0.1:8000", "[::1]:8000", "LOCALHOST"])
    def test_any_loopback_name_works(self, local, host):
        assert local(host=host).get("/api/auth/me").status_code == 200

    def test_ipv6_loopback_peer_works(self, local):
        assert local(peer=("::1", 50000)).get("/api/auth/me").status_code == 200

    def test_the_dev_servers_proxied_request_still_works(self, local):
        # Vite forwards the browser's Origin (its own address) and Host unchanged
        c = local(host="localhost:5173")
        assert c.post("/api/clients", json={"display_name": "A", "payor": "aetna"}, headers={"Origin": "http://localhost:5173"}).status_code == 201

    @pytest.mark.parametrize(
        "peer, host, headers, reason",
        [
            (("203.0.113.5", 4000), "localhost", {}, "connection is from another machine"),
            (("127.0.0.1", 4000), "myapp.example.com", {}, "addressed to another name (DNS rebinding)"),
            (("127.0.0.1", 4000), "localhost", {"X-Forwarded-For": "203.0.113.5"}, "came through a proxy"),
            (("127.0.0.1", 4000), "localhost", {"X-Real-IP": "203.0.113.5"}, "came through a proxy"),
            (("127.0.0.1", 4000), "localhost", {"Forwarded": "for=203.0.113.5"}, "came through a proxy"),
            (("127.0.0.1", 4000), "localhost", {"Sec-Fetch-Site": "cross-site"}, "browser says another site caused it"),
            (("127.0.0.1", 4000), "localhost", {"Origin": "https://evil.example"}, "script on another site"),
        ],
    )
    def test_refused_unless_it_is_plainly_local(self, local, peer, host, headers, reason):
        c = local(host=host, peer=peer)
        assert c.get("/api/auth/me", headers=headers).status_code == 401, reason
        assert c.get("/api/clients", headers=headers).status_code == 401, reason

    def test_another_site_cannot_trigger_a_change_with_a_form_post(self, local):
        victim = local().post("/api/clients", json={"display_name": "Victim", "payor": "aetna"}).json()
        forged = local().post(f"/api/clients/{victim['id']}/archive", headers={"Origin": "https://evil.example"})
        assert forged.status_code == 401
        assert len(local().get("/api/clients").json()) == 1  # still there

    def test_a_real_login_still_works_and_is_not_marked_local(self, local):
        c = local()
        assert c.post("/api/auth/login", json={"username": "tester", "password": "pw-123"}).status_code == 200
        assert c.get("/api/auth/me").json().get("local") is not True

    def test_the_skip_does_not_open_the_login_route_to_bad_passwords(self, local):
        assert local().post("/api/auth/login", json={"username": "tester", "password": "wrong"}).status_code == 401


class TestServingTheFrontend:
    """In production the API serves the built frontend, with the app's own routes as a fallback."""

    @pytest.fixture
    def site(self, tmp_path, monkeypatch):
        dist = tmp_path / "dist"
        (dist / "assets").mkdir(parents=True)
        (dist / "index.html").write_text("<html>the app</html>")
        (dist / "assets" / "app.js").write_text("console.log('hi')")
        (dist / "favicon.svg").write_text("<svg/>")
        (tmp_path / "secret.txt").write_text("outside the build folder")
        monkeypatch.setattr("api.main.WEB_DIST", dist)

        config = tmp_path / "auth.yaml"
        config.write_text(yaml.dump({"credentials": {"usernames": {}}, "cookie": {"name": "c", "key": "k", "expiry_days": 1}}))
        monkeypatch.setattr("auth_config.AUTH_CONFIG_PATH", config)
        monkeypatch.setattr("data.store.DB_PATH", TEST_DB_PATH)

        from api.main import create_app

        with TestClient(create_app()) as client:
            yield client
        for suffix in ("", "-wal", "-shm"):
            extra = Path(str(TEST_DB_PATH) + suffix)
            if extra.exists():
                os.remove(extra)

    def test_the_root_and_any_app_route_return_the_page(self, site):
        for path in ("/", "/import", "/clients", "/some/deep/link"):
            response = site.get(path)
            assert response.status_code == 200 and "the app" in response.text, path

    def test_built_files_are_served(self, site):
        assert site.get("/assets/app.js").text == "console.log('hi')"
        assert site.get("/favicon.svg").text == "<svg/>"

    def test_unknown_api_paths_are_404_not_the_page(self, site):
        response = site.get("/api/nope")
        assert response.status_code == 404 and "the app" not in response.text

    def test_nothing_outside_the_build_folder_is_reachable(self, site):
        for path in ("/../secret.txt", "/%2e%2e/secret.txt", "/assets/../../secret.txt", "/..%2fsecret.txt"):
            assert "outside the build folder" not in site.get(path).text, path

    def test_the_page_is_rechecked_every_load_so_a_rebuild_is_never_hidden(self, site):
        for path in ("/", "/import", "/some/deep/link", "/favicon.svg"):
            assert site.get(path).headers["cache-control"] == "no-cache", path

    def test_hashed_assets_are_cached_for_a_year(self, site):
        cache = site.get("/assets/app.js").headers["cache-control"]
        assert "max-age=31536000" in cache and "immutable" in cache

    def test_missing_assets_are_not_marked_cacheable(self, site):
        response = site.get("/assets/nope.js")
        assert response.status_code == 404 and "immutable" not in response.headers.get("cache-control", "")

    def test_the_api_still_works_alongside(self, site):
        assert site.get("/api/health").json() == {"ok": True}
        assert site.get("/api/payors").status_code == 401  # still behind login
