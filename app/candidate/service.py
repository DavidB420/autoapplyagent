import json
from sqlalchemy import select
from sqlalchemy.orm import Session

from ..models import CandidateProfile


def get_or_create_profile(db: Session) -> CandidateProfile:
    profile = db.scalar(select(CandidateProfile).order_by(CandidateProfile.id).limit(1))
    if profile is None:
        profile = CandidateProfile()
        db.add(profile)
        db.commit()
        db.refresh(profile)
    return profile


def profile_to_dict(profile: CandidateProfile) -> dict:
    try:
        structured = json.loads(profile.profile_json or "{}")
    except json.JSONDecodeError:
        structured = {}
    return {
        "id": profile.id,
        "full_name": profile.full_name,
        "email": profile.email,
        "phone": profile.phone,
        "location": profile.location,
        "resume_text": profile.resume_text,
        "structured_profile": structured,
        "updated_at": profile.updated_at,
    }
