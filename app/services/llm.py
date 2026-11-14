from dataclasses import dataclass
import json
import httpx
from ..config import settings


@dataclass
class AnswerResult:
    answer: str
    source: str
    needs_review: bool = True
    evidence: str | None = None


class LLMClient:
    async def answer(self, question: str, candidate_context: str) -> AnswerResult:
        if not settings.llm_base_url or not settings.llm_model:
            return AnswerResult("", "unconfigured", True, "LLM endpoint or model is not configured")

        headers = {}
        if settings.llm_api_key:
            headers["Authorization"] = f"Bearer {settings.llm_api_key}"

        payload = {
            "model": settings.llm_model,
            "temperature": 0.2,
            "messages": [
                {
                    "role": "system",
                    "content": (
                        "You help draft truthful job-application answers. Use only facts in the candidate context. "
                        "Never invent qualifications, dates, employers, skills, work authorization, or achievements. "
                        "If the context does not support an answer, set needs_review=true and explain what is missing. "
                        "Return ONLY valid JSON with keys: answer (string), needs_review (boolean), evidence (string). "
                        "Evidence should identify the resume/profile facts supporting the answer. "
                        "A human must review every answer before it is submitted."
                    ),
                },
                {
                    "role": "user",
                    "content": f"Candidate context:\n{candidate_context}\n\nApplication question:\n{question}",
                },
            ],
        }

        async with httpx.AsyncClient(timeout=60) as client:
            response = await client.post(settings.llm_base_url, json=payload, headers=headers)
            response.raise_for_status()
            data = response.json()

        content = data["choices"][0]["message"]["content"].strip()
        try:
            parsed = json.loads(content)
            answer = str(parsed.get("answer", "")).strip()
            needs_review = bool(parsed.get("needs_review", True))
            evidence = str(parsed.get("evidence", "")).strip() or None
        except (json.JSONDecodeError, AttributeError, TypeError):
            answer, needs_review, evidence = content, True, "The model did not return the required JSON format"

        return AnswerResult(answer, "llm", needs_review, evidence)
