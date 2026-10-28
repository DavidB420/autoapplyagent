import asyncio
from contextlib import asynccontextmanager
from fastapi import FastAPI, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session
from .db import SessionLocal, init_db
from .models import Job, Application, ApplicationStatus, ApplicationEvent
from .schemas import JobCreate, JobResponse, ApplicationResponse
from .services.worker import ApplicationWorker

worker = ApplicationWorker()

def db_session():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

@asynccontextmanager
async def lifespan(app: FastAPI):
    init_db()
    task = asyncio.create_task(worker.start())
    yield
    await worker.stop()
    task.cancel()
    try:
        await task
    except asyncio.CancelledError:
        pass

app = FastAPI(title="Pi Job Application Agent", version="0.1.0", lifespan=lifespan)

@app.get("/health")
def health():
    return {"status": "ok", "worker_running": worker.running}

@app.post("/jobs", response_model=JobResponse)
def create_job(payload: JobCreate, db: Session = Depends(db_session)):
    existing = db.scalar(select(Job).where(Job.external_id == payload.external_id))
    if existing:
        return existing
    job = Job(**payload.model_dump(mode="json"))
    db.add(job)
    db.commit()
    db.refresh(job)
    return job

@app.post("/jobs/{job_id}/queue", response_model=ApplicationResponse)
def queue_job(job_id: int, db: Session = Depends(db_session)):
    job = db.get(Job, job_id)
    if not job:
        raise HTTPException(404, "Job not found")
    existing = db.scalar(select(Application).where(Application.job_id == job_id))
    if existing:
        return existing
    application = Application(job_id=job_id, status=ApplicationStatus.DISCOVERED.value)
    db.add(application)
    db.commit()
    db.refresh(application)
    return application

@app.get("/applications", response_model=list[ApplicationResponse])
def list_applications(db: Session = Depends(db_session)):
    return list(db.scalars(select(Application).order_by(Application.id.desc())))

@app.get("/applications/{application_id}", response_model=ApplicationResponse)
def get_application(application_id: int, db: Session = Depends(db_session)):
    application = db.get(Application, application_id)
    if not application:
        raise HTTPException(404, "Application not found")
    return application

@app.get("/applications/{application_id}/events")
def application_events(application_id: int, db: Session = Depends(db_session)):
    if not db.get(Application, application_id):
        raise HTTPException(404, "Application not found")
    events = db.scalars(
        select(ApplicationEvent)
        .where(ApplicationEvent.application_id == application_id)
        .order_by(ApplicationEvent.id)
    )
    return [
        {"id": e.id, "from": e.from_status, "to": e.to_status,
         "message": e.message, "created_at": e.created_at}
        for e in events
    ]

@app.post("/worker/stop")
async def stop_worker():
    await worker.stop()
    return {"worker_running": worker.running}
