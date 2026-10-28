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
