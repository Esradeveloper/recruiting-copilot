"""Extract plain text from a CV PDF."""

import io

from pypdf import PdfReader
from pypdf.errors import PdfReadError

MAX_PAGES = 10


class PdfTextError(ValueError):
    pass


def extract_text(pdf_bytes: bytes) -> str:
    try:
        reader = PdfReader(io.BytesIO(pdf_bytes))
    except PdfReadError as e:
        raise PdfTextError(f"not a readable PDF: {e}") from e

    if len(reader.pages) > MAX_PAGES:
        raise PdfTextError(f"PDF has {len(reader.pages)} pages, limit is {MAX_PAGES}")

    text = "\n".join(page.extract_text() or "" for page in reader.pages).strip()
    if not text:
        # Scanned PDFs have no text layer; OCR is out of scope.
        raise PdfTextError("PDF contains no extractable text")
    return text
