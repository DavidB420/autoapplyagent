import json
from fastapi import APIRouter, Depends, File, HTTPException, UploadFile
from sqlalchemy.orm import Session

from ..db import SessionLocal
from ..models import CandidateProfile
from ..schemas import CandidateProfileUpdate
from .resume_parser import extract_resume_text
from .service import get_or_create_profile, profile_to_dict

router = APIRouter(prefix="/candidate", tags=["candidate"])


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
        profile.profile_json = json.dumps(structured, ensure_ascii=False)
    db.commit()
    db.refresh(profile)
    return profile_to_dict(profile)


@router.post("/resume")
async def upload_resume(file: UploadFile = File(...), db: Session = Depends(db_session)):
    try:
        content = await file.read()
        text = extract_resume_text(file.filename or "resume", content)
    except Exception as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    finally:
        await file.close()

    profile = get_or_create_profile(db)
    profile.resume_text = text
    db.commit()
    db.refresh(profile)
    return {"filename": file.filename, "characters_extracted": len(text), "profile": profile_to_dict(profile)}
