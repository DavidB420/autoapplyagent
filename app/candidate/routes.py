import hashlib
import json
import uuid
from pathlib import Path

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile
from fastapi.responses import FileResponse
from sqlalchemy import select
from sqlalchemy.orm import Session

from ..db import SessionLocal
from ..models import CandidateDocument, CandidateProfile
from ..config import settings
from ..services.llm import LLMClient
from ..schemas import CandidateProfileUpdate
from .resume_parser import extract_resume_text
from .service import get_or_create_profile, profile_to_dict

router = APIRouter(prefix="/candidate", tags=["candidate"])
llm_client = LLMClient()
MAX_UPLOAD_BYTES = 10 * 1024 * 1024
DOCUMENT_TYPES = {"cover_letter", "transcript", "certificate", "portfolio", "other"}


def db_session():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


@router.get("")
def get_candidate(db: Session = Depends(db_session)):
    return profile_to_dict(get_or_create_profile(db))


@router.put("/profile")
def update_candidate(payload: CandidateProfileUpdate, db: Session = Depends(db_session)):
    profile = get_or_create_profile(db)
    values = payload.model_dump(exclude_unset=True)
    structured = values.pop("structured_profile", None)
    for field, value in values.items():
        setattr(profile, field, value)
    if structured is not None:
        try:
            existing_structured = json.loads(profile.profile_json or "{}")
        except json.JSONDecodeError:
            existing_structured = {}
        if not isinstance(existing_structured, dict):
            existing_structured = {}
        # Preserve the LLM extraction when manually editing other profile facts.
        if "resume_extraction" in existing_structured:
            structured = dict(structured)
            structured.setdefault("resume_extraction", existing_structured["resume_extraction"])
        profile.profile_json = json.dumps(structured, ensure_ascii=False)
    db.commit()
    db.refresh(profile)
    return profile_to_dict(profile)


@router.post("/resume")
async def upload_resume(file: UploadFile = File(...), db: Session = Depends(db_session)):
    try:
        content = await file.read(MAX_UPLOAD_BYTES + 1)
        if len(content) > MAX_UPLOAD_BYTES:
            raise ValueError("Resume must be 10 MB or smaller")
        text = extract_resume_text(file.filename or "resume", content)
    except Exception as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    finally:
        await file.close()

    profile = get_or_create_profile(db)
    profile.resume_text = text
    extraction_status = "not_configured"
    extraction_error = None
    try:
        extracted = await llm_client.extract_resume(text)
        try:
            structured = json.loads(profile.profile_json or "{}")
        except json.JSONDecodeError:
            structured = {}
        if not isinstance(structured, dict):
            structured = {}
        structured["resume_extraction"] = extracted
        profile.profile_json = json.dumps(structured, ensure_ascii=False)
        extraction_status = "completed"
    except RuntimeError as exc:
        extraction_error = str(exc)
    except Exception as exc:
        # Preserve the uploaded resume even if the LLM is unavailable or returns invalid JSON.
        extraction_status = "failed"
        extraction_error = str(exc)

    db.commit()
    db.refresh(profile)
    return {
        "filename": file.filename,
        "characters_extracted": len(text),
        "structured_extraction": extraction_status,
        "extraction_error": extraction_error,
        "profile": profile_to_dict(profile),
    }


@router.post("/documents")
async def upload_document(
    file: UploadFile = File(...),
    document_type: str = Form("other"),
    db: Session = Depends(db_session),
):
    """Store an original supporting document and extract text when its format is supported."""
    if document_type not in DOCUMENT_TYPES:
        raise HTTPException(status_code=400, detail=f"document_type must be one of: {', '.join(sorted(DOCUMENT_TYPES))}")

    content = await file.read(MAX_UPLOAD_BYTES + 1)
    await file.close()
    if not content:
        raise HTTPException(status_code=400, detail="The uploaded document is empty")
    if len(content) > MAX_UPLOAD_BYTES:
        raise HTTPException(status_code=413, detail="Documents must be 10 MB or smaller")

    original_name = Path((file.filename or "document").replace("\\", "/")).name
    extension = Path(original_name).suffix.lower()
    stored_name = f"{uuid.uuid4().hex}{extension}"
    document_dir = settings.data_dir / "documents"
    document_dir.mkdir(parents=True, exist_ok=True)
    destination = document_dir / stored_name

    extracted_text = None
    if extension in {".pdf", ".docx", ".txt", ".md"}:
        try:
            extracted_text = extract_resume_text(original_name, content)
        except Exception:
            # Keep the original even if text extraction is unavailable (e.g. scanned PDF).
            extracted_text = None

    destination.write_bytes(content)
    record = CandidateDocument(
        original_filename=original_name,
        stored_filename=stored_name,
        document_type=document_type,
        content_type=file.content_type,
        size_bytes=len(content),
        sha256=hashlib.sha256(content).hexdigest(),
        extracted_text=extracted_text,
    )
    try:
        db.add(record)
        db.commit()
        db.refresh(record)
    except Exception:
        destination.unlink(missing_ok=True)
        db.rollback()
        raise

    return {
        "id": record.id,
        "filename": record.original_filename,
        "document_type": record.document_type,
        "size_bytes": record.size_bytes,
        "sha256": record.sha256,
        "text_extracted": extracted_text is not None,
        "created_at": record.created_at,
    }


@router.get("/documents")
def list_documents(db: Session = Depends(db_session)):
    documents = db.scalars(select(CandidateDocument).order_by(CandidateDocument.id.desc()))
    return [
        {"id": d.id, "filename": d.original_filename, "document_type": d.document_type,
         "content_type": d.content_type, "size_bytes": d.size_bytes,
         "text_extracted": d.extracted_text is not None, "created_at": d.created_at}
        for d in documents
    ]


@router.get("/documents/{document_id}/download")
def download_document(document_id: int, db: Session = Depends(db_session)):
    document = db.get(CandidateDocument, document_id)
    if document is None:
        raise HTTPException(status_code=404, detail="Document not found")
    path = settings.data_dir / "documents" / document.stored_filename
    if not path.is_file():
        raise HTTPException(status_code=404, detail="Stored document file is missing")
    return FileResponse(path, media_type=document.content_type or "application/octet-stream",
                        filename=document.original_filename)
