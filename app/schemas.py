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
