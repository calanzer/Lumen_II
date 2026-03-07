"""Tests for DOCX upload support in classifier and extractor."""

from io import BytesIO
from pathlib import Path

import pytest
from docx import Document

from pipeline.classifier import classify_document, classify_pdf
from pipeline.extractor import _extract_tables_from_docx, _extract_text_from_docx


FIXTURES = Path(__file__).parent / "fixtures"


@pytest.fixture
def sample_docx_bytes() -> bytes:
    with open(FIXTURES / "sample_progress_report.docx", "rb") as f:
        return f.read()


@pytest.fixture
def sample_pdf_bytes() -> bytes:
    with open(FIXTURES / "sample_progress_report.pdf", "rb") as f:
        return f.read()


# --- Classifier ---

class TestDocxClassifier:
    def test_classifies_docx(self, sample_docx_bytes):
        result = classify_document(sample_docx_bytes, "report.docx")
        assert result["file_type"] == "docx"
        assert result["is_native_digital"] is True
        assert result["page_count"] >= 1

    def test_classifies_pdf(self, sample_pdf_bytes):
        result = classify_document(sample_pdf_bytes, "report.pdf")
        assert result["file_type"] == "pdf"
        assert result["page_count"] >= 1

    def test_docx_detected_by_extension(self, sample_docx_bytes):
        """classify_document routes to DOCX classifier based on filename."""
        result = classify_document(sample_docx_bytes, "CentralReach_Export.DOCX")
        assert result["file_type"] == "docx"

    def test_pdf_backwards_compat(self, sample_pdf_bytes):
        """Legacy classify_pdf still works."""
        result = classify_pdf(sample_pdf_bytes)
        assert result["page_count"] >= 1
        assert "is_native_digital" in result


# --- Text extraction ---

class TestDocxTextExtraction:
    def test_extracts_text_from_docx(self, sample_docx_bytes):
        text = _extract_text_from_docx(sample_docx_bytes)
        assert len(text) > 1000
        assert "CR-2024-0847" in text
        assert "F84.0" in text
        assert "Dr. Maria Gonzalez" in text

    def test_extracts_assessment_data(self, sample_docx_bytes):
        text = _extract_text_from_docx(sample_docx_bytes)
        assert "VB-MAPP" in text
        assert "Vineland" in text
        assert "CARS-2" in text

    def test_extracts_behavior_data(self, sample_docx_bytes):
        text = _extract_text_from_docx(sample_docx_bytes)
        assert "Aggression" in text
        assert "Elopement" in text
        assert "8.3" in text  # baseline
        assert "2.7" in text  # current

    def test_extracts_hours_data(self, sample_docx_bytes):
        text = _extract_text_from_docx(sample_docx_bytes)
        assert "97153" in text
        assert "97155" in text
        assert "624" in text


# --- Table extraction ---

class TestDocxTableExtraction:
    def test_extracts_tables(self, sample_docx_bytes):
        tables = _extract_tables_from_docx(sample_docx_bytes)
        assert len(tables) >= 3  # At least client info, VB-MAPP, hours tables

    def test_table_has_headers_and_data(self, sample_docx_bytes):
        tables = _extract_tables_from_docx(sample_docx_bytes)
        for table in tables:
            assert len(table) >= 2  # header + at least 1 data row
            assert len(table[0]) >= 2  # at least 2 columns

    def test_hours_table_present(self, sample_docx_bytes):
        """Should find a table containing CPT codes."""
        tables = _extract_tables_from_docx(sample_docx_bytes)
        hours_tables = [
            t for t in tables
            if any("97153" in cell for row in t for cell in row)
        ]
        assert len(hours_tables) >= 1

    def test_assessment_table_present(self, sample_docx_bytes):
        """Should find a table containing VB-MAPP domain scores."""
        tables = _extract_tables_from_docx(sample_docx_bytes)
        vbmapp_tables = [
            t for t in tables
            if any("Mand" in cell for row in t for cell in row)
        ]
        assert len(vbmapp_tables) >= 1
