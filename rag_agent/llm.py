"""Answer generation via Anthropic or OpenAI."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable, List

from anthropic import Anthropic
from openai import OpenAI

from .settings import settings


@dataclass
class ContextChunk:
    doc_id: str
    chunk_id: int
    content: str

    @property
    def reference(self) -> str:
        return f"{self.doc_id}#{self.chunk_id}"


_anthropic_client: Anthropic | None = None
_openai_client: OpenAI | None = None


def _get_anthropic() -> Anthropic:
    global _anthropic_client
    if _anthropic_client is None:
        if not settings.anthropic_api_key:
            raise RuntimeError("ANTHROPIC_API_KEY is required for Anthropic provider")
        _anthropic_client = Anthropic(api_key=settings.anthropic_api_key)
    return _anthropic_client


def _get_openai() -> OpenAI:
    global _openai_client
    if _openai_client is None:
        if not settings.openai_api_key:
            raise RuntimeError("OPENAI_API_KEY is required for OpenAI provider")
        _openai_client = OpenAI(api_key=settings.openai_api_key)
    return _openai_client


def _build_prompt(question: str, chunks: Iterable[ContextChunk]) -> str:
    parts = [
        "Du bist ein hilfreicher Assistent. Verwende ausschließlich den bereitgestellten Kontext,",
        "antworte auf Deutsch und zitiere deine Quellen im Format [doc_id#chunk_id].",
        "Wenn der Kontext nicht ausreicht, erkläre dies klar.",
        "\nKontext:\n",
    ]
    for chunk in chunks:
        parts.append(f"[{chunk.reference}]\n{chunk.content}\n")
    parts.append("\nFrage:\n" + question)
    return "\n".join(parts)


def generate_answer(question: str, chunks: List[ContextChunk]) -> str:
    prompt = _build_prompt(question, chunks)
    if settings.llm_provider == "anthropic":
        client = _get_anthropic()
        message = client.messages.create(
            model=settings.llm_model,
            max_tokens=600,
            temperature=0.1,
            messages=[{"role": "user", "content": prompt}],
        )
        return "".join(block.text for block in message.content if hasattr(block, "text"))

    client = _get_openai()
    completion = client.chat.completions.create(
        model=settings.llm_model,
        temperature=0.1,
        messages=[
            {"role": "system", "content": "Beantworte Nutzerfragen präzise."},
            {"role": "user", "content": prompt},
        ],
    )
    return completion.choices[0].message.content or ""


__all__ = ["ContextChunk", "generate_answer"]
