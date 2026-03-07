"""Classify uploaded document (PDF or DOCX) and detect source platform."""

import fitz  # pymupdf
from docx import Document
from io import BytesIO
import math


def _classify_pdf(pdf_bytes: bytes) -> dict:
    """Classify a PDF document."""
    doc = fitz.open(stream=pdf_bytes, filetype="pdf")
    total_text_chars = 0
    has_images = False

    for page in doc:
        text = page.get_text()
        total_text_chars += len(text)
        if page.get_images():
            has_images = True

    page_count = len(doc)
    avg_chars = total_text_chars / max(page_count, 1)

    # Heuristic: scanned PDFs have very low text density
    is_native = avg_chars > 200

    # Source platform detection via header/footer text patterns
    full_text = ""
    for page in doc:
        full_text += page.get_text()

    estimated_source = _detect_source(full_text)
    doc.close()

    return {
        "is_native_digital": is_native,
        "page_count": page_count,
        "has_images": has_images,
        "estimated_source": estimated_source,
        "text_density_per_page": avg_chars,
        "file_type": "pdf",
    }


def _classify_docx(docx_bytes: bytes) -> dict:
    """Classify a DOCX document."""
    doc = Document(BytesIO(docx_bytes))

    full_text = "\n".join(p.text for p in doc.paragraphs)
    total_chars = len(full_text)
    has_images = any(
        run.element.findall('.//{http://schemas.openxmlformats.org/wordprocessingml/2006/main}drawing')
        or run.element.findall('.//{http://schemas.openxmlformats.org/wordprocessingml/2006/main}pict')
        for para in doc.paragraphs
        for run in para.runs
    )

    # Estimate page count (~3000 chars per page for clinical docs)
    estimated_pages = max(1, math.ceil(total_chars / 3000))

    estimated_source = _detect_source(full_text)

    return {
        "is_native_digital": True,  # DOCX is always native digital
        "page_count": estimated_pages,
        "has_images": has_images,
        "estimated_source": estimated_source,
        "text_density_per_page": total_chars / max(estimated_pages, 1),
        "file_type": "docx",
    }


def _detect_source(full_text: str) -> str | None:
    """Detect source platform from document text."""
    text_lower = full_text.lower()
    if "centralreach" in text_lower or "cr " in text_lower[:500]:
        return "centralreach"
    elif "catalyst" in text_lower:
        return "catalyst"
    elif "rethink" in text_lower:
        return "rethink"
    return None


def classify_document(file_bytes: bytes, filename: str) -> dict:
    """
    Classify an uploaded document (PDF or DOCX).

    Returns:
        {
            "is_native_digital": bool,
            "page_count": int,
            "has_images": bool,
            "estimated_source": str | None,
            "text_density_per_page": float,
            "file_type": "pdf" | "docx",
        }
    """
    if filename.lower().endswith(".docx"):
        return _classify_docx(file_bytes)
    else:
        return _classify_pdf(file_bytes)


# Backwards compatibility
def classify_pdf(pdf_bytes: bytes) -> dict:
    """Legacy entry point — classifies a PDF. Use classify_document() for PDF+DOCX."""
    return _classify_pdf(pdf_bytes)
