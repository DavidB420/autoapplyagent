from sqlalchemy.orm import Session
from ..models import Application, ApplicationEvent, ApplicationStatus

ALLOWED = {
    ApplicationStatus.DISCOVERED: {ApplicationStatus.EVALUATED, ApplicationStatus.FAILED},
    ApplicationStatus.EVALUATED: {ApplicationStatus.QUEUED, ApplicationStatus.FAILED},
    ApplicationStatus.QUEUED: {ApplicationStatus.BROWSER_STARTED, ApplicationStatus.FAILED},
    ApplicationStatus.BROWSER_STARTED: {ApplicationStatus.QUESTIONS_EXTRACTED, ApplicationStatus.FAILED},
    ApplicationStatus.QUESTIONS_EXTRACTED: {ApplicationStatus.ANSWERS_GENERATED, ApplicationStatus.FAILED},
    ApplicationStatus.ANSWERS_GENERATED: {ApplicationStatus.FORM_FILLED, ApplicationStatus.FAILED},
    ApplicationStatus.FORM_FILLED: {ApplicationStatus.SUBMITTING, ApplicationStatus.FAILED},
    ApplicationStatus.SUBMITTING: {ApplicationStatus.SUBMITTED, ApplicationStatus.FAILED},
    ApplicationStatus.SUBMITTED: set(),
    ApplicationStatus.FAILED: set(),
}

def transition(db: Session, app: Application, target: ApplicationStatus, message=""):
    current = ApplicationStatus(app.status)
    if target not in ALLOWED[current]:
        raise ValueError(f"Invalid transition: {current.value} -> {target.value}")
    db.add(ApplicationEvent(
        application_id=app.id,
        from_status=current.value,
        to_status=target.value,
        message=message,
    ))
    app.status = target.value
    db.commit()
    db.refresh(app)
    return app
