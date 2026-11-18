from io import BytesIO
from pathlib import Path

from docx import Document
from pypdf import PdfReader

MAX_RESUME_BYTES = 10 * 1024 * 1024


def extract_resume_text(filename: str, content: bytes) -> str:
    """Extract text from a PDF, DOCX, or plain-text resume."""
    if not content:
        raise ValueError("The uploaded resume is empty")
    if len(content) > MAX_RESUME_BYTES:
        raise ValueError("Resume must be 10 MB or smaller")

    extension = Path(filename or "").suffix.lower()
    if extension == ".pdf":
        text = "\n".join(page.extract_text() or "" for page in PdfReader(BytesIO(content)).pages)
    elif extension == ".docx":
        document = Document(BytesIO(content))
        text = "\n".join(p.text for p in document.paragraphs)
        for table in document.tables:
            for row in table.rows:
                text += "\n" + " | ".join(cell.text for cell in row.cells)
    elif extension in {".txt", ".md"}:
        text = content.decode("utf-8-sig")
    else:
        raise ValueError("Unsupported file type. Upload a PDF, DOCX, or TXT resume.")

    text = "\n".join(line.strip() for line in text.splitlines() if line.strip())
    if not text:
        raise ValueError("No selectable text was found. Scanned PDFs need OCR before upload.")
    return text
