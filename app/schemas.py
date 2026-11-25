from datetime import datetime
from pydantic import BaseModel, HttpUrl

class JobCreate(BaseModel):
    external_id: str
    title: str
    company: str
    location: str | None = None
    url: HttpUrl
    ats: str | None = None
    description: str | None = None

class JobResponse(JobCreate):
    id: int
    model_config = {"from_attributes": True}

class ApplicationResponse(BaseModel):
    id: int
    job_id: int
    status: str
    score: int | None
    error: str | None
    model_config = {"from_attributes": True}


class CandidateProfileUpdate(BaseModel):
    full_name: str | None = None
    email: str | None = None
    phone: str | None = None
    location: str | None = None
    structured_profile: dict | None = None


class AnswerCreate(BaseModel):
    question: str


class AnswerResponse(BaseModel):
    id: int
    question: str
    answer: str
    source: str
    needs_review: bool
    evidence: str | None
    created_at: datetime
    model_config = {"from_attributes": True}
