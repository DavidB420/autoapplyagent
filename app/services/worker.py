import asyncio
from sqlalchemy import select
from sqlalchemy.orm import Session
from ..config import settings
from ..db import SessionLocal
from ..models import Application, ApplicationStatus
from .evaluator import JobEvaluator
from .state_machine import transition
from ..ats.playwright_worker import BrowserWorker

class ApplicationWorker:
    def __init__(self):
        self.running = False
        self.evaluator = JobEvaluator()
        self.browser = BrowserWorker()

    async def start(self):
        await self.browser.start()
        self.running = True
        while self.running:
            try:
                processed = await self.process_one()
                if not processed:
                    await asyncio.sleep(settings.worker_poll_seconds)
            except asyncio.CancelledError:
                break
            except Exception:
                await asyncio.sleep(settings.worker_poll_seconds)
        await self.browser.stop()

    async def stop(self):
        self.running = False

    async def process_one(self):
        db: Session = SessionLocal()
        app = None
        try:
            app = db.scalar(
                select(Application)
                .where(Application.status.in_([
                    ApplicationStatus.DISCOVERED.value,
                    ApplicationStatus.EVALUATED.value,
                    ApplicationStatus.QUEUED.value,
                ]))
                .order_by(Application.id)
            )
            if not app:
                return False

            if app.status == ApplicationStatus.DISCOVERED.value:
                app.score = self.evaluator.score(app.job)
                db.commit()
                transition(db, app, ApplicationStatus.EVALUATED, f"score={app.score}")

            if app.status == ApplicationStatus.EVALUATED.value:
                if (app.score or 0) < 30:
                    transition(db, app, ApplicationStatus.FAILED, "Below minimum score")
                    return True
                transition(db, app, ApplicationStatus.QUEUED)

            if app.status == ApplicationStatus.QUEUED.value:
                transition(db, app, ApplicationStatus.BROWSER_STARTED)
                page = await self.browser.open(app.job.url)
                transition(db, app, ApplicationStatus.QUESTIONS_EXTRACTED,
                            f"Opened {page.url}")
                transition(db, app, ApplicationStatus.ANSWERS_GENERATED,
                            "Placeholder: ATS adapter must supply questions")
                transition(db, app, ApplicationStatus.FAILED,
                            "No ATS adapter configured")
                await page.close()
                return True

            return True
        except Exception as exc:
            if app and app.status not in {
                ApplicationStatus.SUBMITTED.value,
                ApplicationStatus.FAILED.value,
            }:
                try:
                    transition(db, app, ApplicationStatus.FAILED, str(exc))
                except Exception:
                    pass
            return True
        finally:
            db.close()
