"""Tests for the SQLite persistence layer."""

import json
import os
from pathlib import Path

import pytest

# Override DB path before importing store
TEST_DB_PATH = Path(__file__).parent / "fixtures" / "test_store.db"


@pytest.fixture(autouse=True)
def clean_db(monkeypatch):
    """Use a test database and clean up after each test."""
    monkeypatch.setattr("data.store.DB_PATH", TEST_DB_PATH)
    # Re-init with test path
    from data.store import init_db
    init_db()
    yield
    if TEST_DB_PATH.exists():
        os.remove(TEST_DB_PATH)


@pytest.fixture
def sample_clinical_data():
    from schemas.clinical_data import ExtractedClinicalData
    fixture_path = Path(__file__).parent / "fixtures" / "realistic_extraction.json"
    with open(fixture_path) as f:
        data = json.load(f)
    return ExtractedClinicalData.model_validate(data)


@pytest.fixture
def sample_narrative():
    from schemas.narrative import AnthemReauthNarrative
    fixture_path = Path(__file__).parent / "fixtures" / "realistic_narrative.json"
    with open(fixture_path) as f:
        data = json.load(f)
    return AnthemReauthNarrative.model_validate(data)


class TestClientCRUD:
    def test_create_and_get_client(self):
        from data.store import create_client, get_client
        cid = create_client("Martinez, A.", client_identifier="CR-2024-0847", diagnosis_codes=["F84.0"])
        client = get_client(cid)
        assert client is not None
        assert client["display_name"] == "Martinez, A."
        assert client["client_identifier"] == "CR-2024-0847"
        assert client["diagnosis_codes"] == ["F84.0"]
        assert client["status"] == "active"

    def test_list_clients(self):
        from data.store import create_client, list_clients
        create_client("Client A")
        create_client("Client B")
        clients = list_clients()
        assert len(clients) == 2
        names = [c["display_name"] for c in clients]
        assert "Client A" in names
        assert "Client B" in names

    def test_update_client(self):
        from data.store import create_client, update_client, get_client
        cid = create_client("Old Name")
        update_client(cid, display_name="New Name", diagnosis_codes=["F84.0", "F80.2"])
        client = get_client(cid)
        assert client["display_name"] == "New Name"
        assert client["diagnosis_codes"] == ["F84.0", "F80.2"]

    def test_delete_client(self):
        from data.store import create_client, delete_client, get_client
        cid = create_client("To Delete")
        delete_client(cid)
        assert get_client(cid) is None

    def test_list_excludes_discharged(self):
        from data.store import create_client, update_client, list_clients
        cid1 = create_client("Active")
        cid2 = create_client("Discharged")
        update_client(cid2, status="discharged")
        clients = list_clients(status="active")
        assert len(clients) == 1
        assert clients[0]["display_name"] == "Active"


class TestAuthPeriodCRUD:
    def test_create_and_get_period(self):
        from data.store import create_client, create_auth_period, get_auth_period
        cid = create_client("Test")
        pid = create_auth_period(cid, "2025-07-01", "2025-12-31")
        period = get_auth_period(pid)
        assert period is not None
        assert period["period_start"] == "2025-07-01"
        assert period["period_end"] == "2025-12-31"
        assert period["status"] == "draft"

    def test_list_periods_newest_first(self):
        from data.store import create_client, create_auth_period, list_auth_periods
        cid = create_client("Test")
        create_auth_period(cid, "2025-01-01", "2025-06-30")
        create_auth_period(cid, "2025-07-01", "2025-12-31")
        periods = list_auth_periods(cid)
        assert len(periods) == 2
        assert periods[0]["period_end"] == "2025-12-31"  # newest first
        assert periods[1]["period_end"] == "2025-06-30"


class TestSaveAndLoad:
    def test_save_extraction(self, sample_clinical_data):
        from data.store import create_client, create_auth_period, save_extraction, get_auth_period
        cid = create_client("Test")
        pid = create_auth_period(cid, "2025-07-01", "2025-12-31")
        save_extraction(pid, sample_clinical_data, "test.pdf", {"is_complete": True, "score": 1.0, "missing": [], "warnings": []})
        period = get_auth_period(pid)
        assert period["status"] == "in_progress"
        assert period["uploaded_filename"] == "test.pdf"
        assert period["extracted_data_parsed"] is not None
        assert period["extracted_data_parsed"].client.client_id == "CR-2024-0847"

    def test_save_clinical_data_edits(self, sample_clinical_data):
        from data.store import create_client, create_auth_period, save_extraction, save_clinical_data, get_auth_period
        cid = create_client("Test")
        pid = create_auth_period(cid, "2025-07-01", "2025-12-31")
        save_extraction(pid, sample_clinical_data, "test.pdf")
        # Edit client name
        sample_clinical_data.client.client_id = "EDITED-001"
        save_clinical_data(pid, sample_clinical_data)
        period = get_auth_period(pid)
        assert period["extracted_data_parsed"].client.client_id == "EDITED-001"

    def test_save_narrative(self, sample_clinical_data, sample_narrative):
        from data.store import create_client, create_auth_period, save_extraction, save_narrative, get_auth_period
        cid = create_client("Test")
        pid = create_auth_period(cid, "2025-07-01", "2025-12-31")
        save_extraction(pid, sample_clinical_data, "test.pdf")
        save_narrative(pid, sample_narrative)
        period = get_auth_period(pid)
        assert period["status"] == "generated"
        assert period["narrative_data_parsed"] is not None
        assert period["narrative_data_parsed"].overall_confidence == 0.95

    def test_save_export(self, sample_clinical_data, sample_narrative):
        from data.store import create_client, create_auth_period, save_extraction, save_narrative, save_export, get_auth_period
        cid = create_client("Test")
        pid = create_auth_period(cid, "2025-07-01", "2025-12-31")
        save_extraction(pid, sample_clinical_data, "test.pdf")
        save_narrative(pid, sample_narrative)
        save_export(pid)
        period = get_auth_period(pid)
        assert period["status"] == "exported"
        assert period["exported_at"] is not None


class TestPriorPeriod:
    def test_get_prior_period(self, sample_clinical_data):
        from data.store import create_client, create_auth_period, save_extraction, get_prior_period
        cid = create_client("Test")
        pid1 = create_auth_period(cid, "2025-01-01", "2025-06-30")
        pid2 = create_auth_period(cid, "2025-07-01", "2025-12-31")
        save_extraction(pid1, sample_clinical_data, "prior.pdf")
        prior = get_prior_period(cid, pid2)
        assert prior is not None
        assert prior["period_end"] == "2025-06-30"
        assert prior["extracted_data_parsed"] is not None

    def test_no_prior_period_for_first(self):
        from data.store import create_client, create_auth_period, get_prior_period
        cid = create_client("Test")
        pid = create_auth_period(cid, "2025-07-01", "2025-12-31")
        prior = get_prior_period(cid, pid)
        assert prior is None


class TestDashboard:
    def test_dashboard_returns_clients_with_periods(self, sample_clinical_data):
        from data.store import create_client, create_auth_period, save_extraction, get_dashboard_data
        cid = create_client("Dashboard Client", client_identifier="DC-001", diagnosis_codes=["F84.0"])
        pid = create_auth_period(cid, "2025-07-01", "2025-12-31")
        save_extraction(pid, sample_clinical_data, "test.pdf")
        dashboard = get_dashboard_data()
        assert len(dashboard) == 1
        d = dashboard[0]
        assert d["display_name"] == "Dashboard Client"
        assert d["period_end"] == "2025-12-31"
        assert d["urgency"] in ("expired", "critical", "soon", "ok")

    def test_dashboard_sorted_by_expiry(self):
        from data.store import create_client, create_auth_period, get_dashboard_data
        c1 = create_client("Later")
        c2 = create_client("Sooner")
        create_auth_period(c1, "2025-01-01", "2027-12-31")
        create_auth_period(c2, "2025-01-01", "2025-06-30")
        dashboard = get_dashboard_data()
        assert dashboard[0]["display_name"] == "Sooner"
        assert dashboard[1]["display_name"] == "Later"

    def test_dashboard_client_without_period(self):
        from data.store import create_client, get_dashboard_data
        create_client("No Period")
        dashboard = get_dashboard_data()
        assert len(dashboard) == 1
        assert dashboard[0]["urgency"] == "no_period"
