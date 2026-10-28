from dataclasses import dataclass
from typing import Protocol

@dataclass
class ApplicationQuestion:
    text: str
    required: bool = False

@dataclass
class ApplicationResult:
    submitted: bool
    external_application_id: str | None = None

class ATSAdapter(Protocol):
    name: str
    async def open_application(self, url: str) -> None: ...
    async def get_questions(self) -> list[ApplicationQuestion]: ...
    async def fill_question(self, question: ApplicationQuestion, answer: str) -> None: ...
    async def submit(self) -> ApplicationResult: ...
