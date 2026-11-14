# Pi Job Application Agent

Initial Python/FastAPI codebase for a Raspberry Pi 5 (8 GB).

Architecture:
- FastAPI API
- SQLite + WAL persistence
- Autonomous background worker
- One persistent Playwright browser
- Provider-agnostic cloud LLM adapter
- ATS adapter boundaries for Workday/iCIMS/etc.

Application state:
DISCOVERED -> EVALUATED -> QUEUED -> BROWSER_STARTED -> QUESTIONS_EXTRACTED
-> ANSWERS_GENERATED -> FORM_FILLED -> SUBMITTING -> SUBMITTED

This starter deliberately does not include site-specific ATS selectors or CAPTCHA
bypassing. Those belong in dedicated adapters and must respect each site's rules.

Run:
    python -m venv .venv
    # Windows PowerShell: .venv\Scripts\Activate.ps1
    # Linux/macOS: source .venv/bin/activate
    pip install -r requirements.txt
    playwright install chromium
    cp .env.example .env
    uvicorn app.main:app --host 0.0.0.0 --port 8000

Docker:
    docker compose up --build

API docs:
    http://localhost:8000/docs

The agent must only submit factual applications and must not fabricate
qualifications, work authorization, education, experience, or answers.

## Candidate profile and answer drafting (added in v0.2)

The candidate knowledge base is stored in the existing SQLite database. No second
engine or database is created. Existing `candidate_profile` data is retained, and
`generated_answers` is added automatically by `create_all` on startup.

- `POST /candidate/resume` — upload a PDF, DOCX, or TXT resume (10 MB maximum).
- `GET /candidate` — read the saved candidate profile and extracted resume text.
- `PUT /candidate/profile` — update contact details and structured profile facts.
- `POST /answers` — draft an answer using the saved profile and configured cloud LLM.
- `GET /answers` and `GET /answers/{answer_id}` — review saved drafts.

Example answer request:

```json
{
  "question": "Describe your experience with Python and machine learning."
}
```

Generated answers are marked `needs_review` by default unless the model explicitly
returns otherwise. Review the answer and its evidence before using it in an application.
The answer endpoint does not submit applications. The existing Workday/iCIMS classes
remain adapter stubs; ATS-specific question extraction, field mapping, and submission
still need to be implemented and tested separately.

The existing `candidate_profile` table is reused. The new `generated_answers` table is
created on startup; this is additive and does not require dropping or replacing the
existing database. For production use, add Alembic migrations before further schema
changes.
