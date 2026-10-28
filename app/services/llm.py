from dataclasses import dataclass
import httpx
from ..config import settings

@dataclass
class AnswerResult:
    answer: str
    source: str

class LLMClient:
    async def answer(self, question: str, candidate_context: str) -> AnswerResult:
        if not settings.llm_base_url:
            return AnswerResult("", "unconfigured")

        headers = {}
        if settings.llm_api_key:
            headers["Authorization"] = f"Bearer {settings.llm_api_key}"

        payload = {
            "model": settings.llm_model,
            "messages": [
                {
                    "role": "system",
                    "content": (
                        "Answer using only the supplied candidate context. "
                        "Never invent qualifications or facts. "
                        "If insufficient, return NEEDS_REVIEW."
                    ),
                },
                {
                    "role": "user",
                    "content": f"Candidate context:\n{candidate_context}\n\nQuestion:\n{question}",
                },
            ],
        }

        async with httpx.AsyncClient(timeout=60) as client:
            response = await client.post(settings.llm_base_url, json=payload, headers=headers)
            response.raise_for_status()
            data = response.json()

        return AnswerResult(
            data["choices"][0]["message"]["content"].strip(),
            "llm",
        )
