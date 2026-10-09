from pathlib import Path

import pytest

from app.pdf_text import PdfTextError, extract_text

CVS = Path(__file__).resolve().parent.parent / "data" / "cvs"


def test_extracts_text_from_fictional_cv():
    text = extract_text((CVS / "cv_01_strong_ai.pdf").read_bytes())
    assert "Automation Engineer" in text
    assert "n8n" in text


def test_rejects_non_pdf():
    with pytest.raises(PdfTextError):
        extract_text(b"this is not a pdf")
