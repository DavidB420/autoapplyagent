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
