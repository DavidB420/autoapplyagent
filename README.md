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


## Structured resume extraction and supporting documents (v0.3)

- `POST /candidate/resume` — extracts selectable text from PDF/DOCX/TXT, saves it in the candidate profile, and asks the configured LLM to produce structured JSON for contact details, summary, skills, education, experience, projects, certifications, and uncertain fields. The extraction is stored under `structured_profile.resume_extraction`; existing manually entered profile data is preserved. If the LLM is not configured or fails, the raw resume text is still saved and the response reports the extraction status.
- `POST /candidate/documents` — saves an original copy of a supporting document under `data/documents/` and stores its metadata in SQLite. Use multipart fields `file` and `document_type`. Supported document types: `cover_letter`, `transcript`, `certificate`, `portfolio`, `other`. PDF/DOCX/TXT/MD text is also extracted when possible, but the original file is retained regardless.
- `GET /candidate/documents` — list saved documents.
- `GET /candidate/documents/{id}/download` — download the original uploaded file.

Uploaded supporting documents are limited to 10 MB each. Docker Compose already mounts `./data` to `/app/data`, so the originals persist across container rebuilds and restarts. Keep `data/` private because it contains personal application documents. Scanned PDF OCR, advanced layout/table reconstruction, and human review/editing of extracted structured fields are not included yet.

## Using Ollama (local LLM)

1. Install Ollama and pull a model: `ollama pull qwen2.5:3b`.
2. Set `LLM_BASE_URL`, `LLM_MODEL` in `.env` (see `.env.example`). `LLM_BASE_URL` must be the full
   chat-completions endpoint, e.g. `http://127.0.0.1:11434/v1/chat/completions`.
3. If the app runs in Docker, `127.0.0.1` points at the container. Use
   `http://host.docker.internal:11434/v1/chat/completions` (the compose file maps this name), and make Ollama
   listen on all interfaces: `OLLAMA_HOST=0.0.0.0` (for a systemd service, `sudo systemctl edit ollama`
   and add `Environment="OLLAMA_HOST=0.0.0.0"`). `0.0.0.0` exposes Ollama to your network; avoid on public Wi-Fi.
4. After code changes, rebuild: `docker compose up -d --build`. After `.env`/compose changes:
   `docker compose up -d --force-recreate`.

Structured extraction on CPU can take several minutes; the extraction timeout is 600 seconds. On success,
empty `full_name`, `email`, `phone` and `location` are filled from the extraction (manual values are never overwritten).
