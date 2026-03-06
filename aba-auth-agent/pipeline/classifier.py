"""Classify PDF as native digital or scanned, and detect source platform."""

import fitz  # pymupdf


def classify_pdf(pdf_bytes: bytes) -> dict:
    """
    Returns:
        {
            "is_native_digital": bool,
            "page_count": int,
            "has_images": bool,
            "estimated_source": str | None,  # "centralreach", "catalyst", "rethink", "unknown"
            "text_density_per_page": float,
        }
    """
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

    estimated_source = None
    text_lower = full_text.lower()
    if "centralreach" in text_lower or "cr " in text_lower[:500]:
        estimated_source = "centralreach"
    elif "catalyst" in text_lower:
        estimated_source = "catalyst"
    elif "rethink" in text_lower:
        estimated_source = "rethink"

    doc.close()

    return {
        "is_native_digital": is_native,
        "page_count": page_count,
        "has_images": has_images,
        "estimated_source": estimated_source,
        "text_density_per_page": avg_chars,
    }
