import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import DeclarativeBase

from app.candidate.resume_parser import extract_resume_text
from app.models import Base, GeneratedAnswer


def test_extract_plain_text_resume():
    result = extract_resume_text("resume.txt", b"David Badiei\nPython Developer\n")
    assert result == "David Badiei\nPython Developer"


def test_reject_unsupported_resume_type():
    with pytest.raises(ValueError):
        extract_resume_text("resume.rtf", b"resume")


def test_generated_answer_table_is_registered():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    assert "generated_answers" in Base.metadata.tables
    engine.dispose()


def test_candidate_document_model_is_registered():
    from app.db import Base
    from app.models import CandidateDocument

    assert CandidateDocument.__tablename__ == "candidate_documents"
    assert "candidate_documents" in Base.metadata.tables


def test_structured_resume_extraction_parses_json(monkeypatch):
    import asyncio
    import json
    from types import SimpleNamespace

    from app.services.llm import LLMClient
    from app.config import settings

    monkeypatch.setattr(settings, "llm_base_url", "https://llm.example/v1/chat/completions")
    monkeypatch.setattr(settings, "llm_model", "test-model")

    response_payload = {
        "choices": [{
            "message": {
                "content": json.dumps({
                    "full_name": "Test Candidate",
                    "contact": {"email": "test@example.com", "phone": None, "location": None, "links": []},
                    "skills": ["Python"],
                    "education": [],
                    "experience": [],
                    "projects": [],
                    "certifications": [],
                    "additional_sections": [],
                    "uncertain_or_missing": [],
                })
            }
        }]
    }

    class FakeResponse:
        def raise_for_status(self):
            pass

        def json(self):
            return response_payload

    class FakeAsyncClient:
        def __init__(self, *args, **kwargs):
            pass

        async def __aenter__(self):
            return self

        async def __aexit__(self, *args):
            pass

        async def post(self, *args, **kwargs):
            return FakeResponse()

    monkeypatch.setattr("app.services.llm.httpx.AsyncClient", FakeAsyncClient)
    result = asyncio.run(LLMClient().extract_resume("Test Candidate - Python"))
    assert result["full_name"] == "Test Candidate"
    assert result["skills"] == ["Python"]
