import logging
import re
from io import BytesIO

from pypdf import PdfReader
logger = logging.getLogger(__name__)

MIN_TEXT_CHARS = 100
MAX_PAGES = 20
MAX_TEXT_CHARS = 30_000  # keeps LLM prompts and DB rows bounded

class ResumeExtractionError(Exception):
    """Raised when text cannot be extracted from an uploaded resume."""

def extract_resume_text(file_bytes: bytes) -> str:
    if not file_bytes:
        raise ResumeExtractionError("The uploaded file is empty.")

    # A real PDF starts with %PDF within the first 1 KB
    if b"%PDF" not in file_bytes[:1024]:
        raise ResumeExtractionError("This file is not a valid PDF.")
    try:
        reader = PdfReader(BytesIO(file_bytes))
        if reader.is_encrypted:
            # Many PDFs are "encrypted" with an empty password; try that first
            if not reader.decrypt(""):
                raise ResumeExtractionError(
                    "The PDF is password-protected. Please upload an unlocked copy.")
        if len(reader.pages) > MAX_PAGES:
            raise ResumeExtractionError(
                f"The PDF has too many pages (max {MAX_PAGES}). Please upload your resume only.")

        pages_text = []
        for page in reader.pages:
            try:
                pages_text.append(page.extract_text() or "")
            except Exception:
                # One bad page should not fail the whole resume
                logger.warning("Skipped an unreadable PDF page", exc_info=True)
                continue
    except Exception as exc:
        if isinstance(exc, ResumeExtractionError):
            raise
        logger.exception("Unexpected error while reading PDF")
        raise ResumeExtractionError("Could not read the PDF. Please try a different file.") from exc
    text = "\n".join(pages_text)
    text = text.replace("\x00", "")              # NUL characters break DB inserts
    text = re.sub(r"[ \t]+", " ", text)          # collapse runs of spaces/tabs
    text = re.sub(r"\n\s*\n+", "\n\n", text)     # collapse repeated blank lines
    text = text.strip()

    if len(text) < MIN_TEXT_CHARS:
        raise ResumeExtractionError("No readable text found. The resume may be a scanned image; ""please upload a text-based PDF.")
    return text[:MAX_TEXT_CHARS]