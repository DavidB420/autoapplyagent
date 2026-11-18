from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from ..db import SessionLocal
from ..models import GeneratedAnswer
from ..schemas import AnswerCreate, AnswerResponse
from ..candidate.service import get_or_create_profile
from ..services.llm import LLMClient

router = APIRouter(prefix="/answers", tags=["answers"])
llm_client = LLMClient()


def db_session():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


@router.post("", response_model=AnswerResponse)
async def generate_answer(payload: AnswerCreate, db: Session = Depends(db_session)):
    profile = get_or_create_profile(db)
    context_parts = [
        f"Name: {profile.full_name or ''}",
        f"Email: {profile.email or ''}",
        f"Phone: {profile.phone or ''}",
        f"Location: {profile.location or ''}",
        f"Resume:\n{profile.resume_text or ''}",
        f"Structured profile:\n{profile.profile_json or '{}'}",
    ]
    context = "\n\n".join(context_parts)
    if not profile.resume_text and not profile.profile_json:
        raise HTTPException(status_code=409, detail="Upload a resume or add candidate profile information first.")

    result = await llm_client.answer(payload.question, context)
    record = GeneratedAnswer(
        question=payload.question,
        answer=result.answer,
        source=result.source,
        needs_review=result.needs_review,
        evidence=result.evidence,
    )
    db.add(record)
    db.commit()
    db.refresh(record)
    return record


@router.get("", response_model=list[AnswerResponse])
def list_answers(limit: int = 50, db: Session = Depends(db_session)):
    limit = max(1, min(limit, 200))
    return list(db.scalars(select(GeneratedAnswer).order_by(GeneratedAnswer.id.desc()).limit(limit)))


@router.get("/{answer_id}", response_model=AnswerResponse)
def get_answer(answer_id: int, db: Session = Depends(db_session)):
    answer = db.get(GeneratedAnswer, answer_id)
    if answer is None:
        raise HTTPException(status_code=404, detail="Answer not found")
    return answer
