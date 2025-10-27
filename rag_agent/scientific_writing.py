"""Scientific writing module with Harvard citation style."""
from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Dict, List

from .embeddings import embed_texts
from .llm import _get_anthropic, _get_openai
from .rerank import RerankCandidate, rerank
from .retrieval import RetrievedChunk, similarity_search
from .settings import settings


class PaperSection(Enum):
    """Scientific paper section types."""
    ABSTRACT = "abstract"
    INTRODUCTION = "introduction"
    LITERATURE_REVIEW = "literature_review"
    METHODOLOGY = "methodology"
    RESULTS = "results"
    DISCUSSION = "discussion"
    CONCLUSION = "conclusion"


SECTION_NAMES_DE = {
    PaperSection.ABSTRACT: "Abstract/Zusammenfassung",
    PaperSection.INTRODUCTION: "Einleitung",
    PaperSection.LITERATURE_REVIEW: "Literaturübersicht",
    PaperSection.METHODOLOGY: "Methodik",
    PaperSection.RESULTS: "Ergebnisse",
    PaperSection.DISCUSSION: "Diskussion",
    PaperSection.CONCLUSION: "Schlussfolgerung",
}


@dataclass
class Citation:
    """Harvard-style citation."""
    doc_id: str
    chunk_id: int
    authors: str | None = None
    year: str | None = None

    @property
    def in_text(self) -> str:
        """Generate in-text citation in Harvard style."""
        if self.authors and self.year:
            # Extract first author's last name
            first_author = self.authors.split(',')[0].split(' et al.')[0].strip()
            return f"({first_author}, {self.year})"
        # Fallback to document reference
        return f"({self.doc_id})"

    @property
    def reference(self) -> str:
        """Generate full reference in Harvard style."""
        if self.authors and self.year:
            return f"{self.authors} ({self.year}). {self.doc_id}"
        return f"{self.doc_id}"


@dataclass
class ScientificText:
    """Generated scientific text with citations."""
    text: str
    citations: List[Citation]
    sources: List[RetrievedChunk]
    reference_list: str


def _extract_metadata(chunk: RetrievedChunk) -> Dict[str, str]:
    """Extract metadata for citations from chunk."""
    meta = chunk.meta or {}
    return {
        'authors': meta.get('authors', ''),
        'year': meta.get('year', ''),
        'title': meta.get('title', chunk.doc_id),
    }


def _build_harvard_references(citations: List[Citation]) -> str:
    """Build Harvard-style reference list."""
    if not citations:
        return ""

    references = []
    seen = set()

    for citation in citations:
        ref_key = f"{citation.authors}_{citation.year}"
        if ref_key not in seen:
            references.append(citation.reference)
            seen.add(ref_key)

    # Sort alphabetically by author
    references.sort()

    return "\n\n**Literaturverzeichnis:**\n\n" + "\n\n".join(references)


def _get_section_prompt(section: PaperSection, topic: str, context: str) -> str:
    """Generate section-specific prompt for scientific writing."""

    base_instruction = f"""Du bist ein wissenschaftlicher Autor. Schreibe einen akademischen Text auf Deutsch im wissenschaftlichen Stil.

WICHTIG:
- Verwende ausschließlich den bereitgestellten Kontext als Grundlage
- Zitiere alle verwendeten Quellen im Harvard-Stil (Autor, Jahr)
- Schreibe objektiv, präzise und wissenschaftlich
- Vermeide persönliche Meinungen und unwissenschaftliche Formulierungen
- Nutze Fachterminologie angemessen
- Strukturiere den Text logisch und kohärent

Thema: {topic}

Kontext aus der Literatur:
{context}

"""

    section_instructions = {
        PaperSection.ABSTRACT: """Schreibe ein prägnantes Abstract (150-250 Wörter), das:
- Den Forschungsgegenstand/das Problem einführt
- Die zentrale Fragestellung oder Hypothese nennt
- Die verwendete Methodik kurz beschreibt
- Die wichtigsten Ergebnisse zusammenfasst
- Die Bedeutung/Implikationen der Ergebnisse aufzeigt

Das Abstract sollte eigenständig verständlich sein und einen vollständigen Überblick bieten.""",

        PaperSection.INTRODUCTION: """Schreibe eine fundierte Einleitung (2-3 Seiten), die:
- Den thematischen Hintergrund und die Relevanz des Forschungsthemas darstellt
- Den aktuellen Forschungsstand skizziert
- Eine Forschungslücke identifiziert
- Die zentrale Forschungsfrage oder Hypothese formuliert
- Die Zielsetzung der Arbeit klar definiert
- Den Aufbau der Arbeit kurz umreißt

Zitiere relevante Literatur, um deine Argumentation zu stützen.""",

        PaperSection.LITERATURE_REVIEW: """Schreibe eine strukturierte Literaturübersicht (3-5 Seiten), die:
- Einen systematischen Überblick über relevante Forschungsarbeiten gibt
- Verschiedene theoretische Ansätze und Perspektiven darstellt
- Zentrale Konzepte, Theorien und Modelle erläutert
- Methodische Ansätze in der Forschung vergleicht
- Konsens und Kontroversen in der Literatur aufzeigt
- Forschungslücken identifiziert
- Einen theoretischen Rahmen für die eigene Arbeit etabliert

Organisiere die Literatur thematisch, chronologisch oder methodisch und zitiere alle Quellen präzise.""",

        PaperSection.METHODOLOGY: """Schreibe einen detaillierten Methodikteil (2-3 Seiten), der:
- Das Forschungsdesign beschreibt (z.B. qualitativ, quantitativ, mixed methods)
- Die Datenerhebungsmethoden erläutert
- Die Stichprobe/das Sample beschreibt (Größe, Auswahl, Eigenschaften)
- Die Datenanalyseverfahren detailliert darstellt
- Verwendete Tools, Instrumente oder Software nennt
- Gütekriterien und Limitationen reflektiert
- Die Vorgehensweise so beschreibt, dass sie replizierbar ist

Begründe methodische Entscheidungen mit Verweis auf die Literatur.""",

        PaperSection.RESULTS: """Schreibe einen klaren Ergebnisteil (3-4 Seiten), der:
- Die Forschungsergebnisse systematisch präsentiert
- Die Daten objektiv und präzise darstellt
- Wichtige Befunde hervorhebt
- Tabellen, Grafiken oder Abbildungen beschreibt (falls im Kontext erwähnt)
- Die Ergebnisse strukturiert nach Forschungsfragen oder Hypothesen
- Quantitative Daten mit statistischen Kennwerten präsentiert
- Qualitative Befunde mit Beispielen illustriert

Interpretiere die Ergebnisse noch NICHT – bleibe deskriptiv.""",

        PaperSection.DISCUSSION: """Schreibe eine kritische Diskussion (3-4 Seiten), die:
- Die wichtigsten Ergebnisse zusammenfasst
- Die Befunde im Kontext der bestehenden Literatur interpretiert
- Übereinstimmungen und Widersprüche zur Forschungsliteratur aufzeigt
- Die Forschungsfragen beantwortet
- Theoretische und praktische Implikationen diskutiert
- Limitationen der Studie kritisch reflektiert
- Stärken der Arbeit herausstellt
- Ansatzpunkte für zukünftige Forschung aufzeigt

Argumentiere differenziert und zitiere relevante Literatur zur Einordnung.""",

        PaperSection.CONCLUSION: """Schreibe eine prägnante Schlussfolgerung (1-2 Seiten), die:
- Die zentralen Ergebnisse zusammenfasst
- Die Forschungsfrage beantwortet
- Den Beitrag zur Forschung herausstellt
- Praktische Implikationen aufzeigt
- Ausblick auf zukünftige Forschung gibt
- Mit einem starken, klaren Schlusssatz endet

Führe KEINE neuen Informationen ein, sondern synthetisiere die wichtigsten Erkenntnisse.""",
    }

    return base_instruction + section_instructions[section]


def generate_scientific_section(
    section: PaperSection,
    topic: str,
    num_sources: int = 8,
) -> ScientificText:
    """
    Generate a scientific paper section with Harvard citations.

    Args:
        section: The type of paper section to generate
        topic: The research topic or question
        num_sources: Number of sources to retrieve (default: 8)

    Returns:
        ScientificText with generated text, citations, and references
    """
    # Retrieve relevant sources
    query_embedding = embed_texts([topic])[0]
    retrieved = similarity_search(query_embedding, limit=num_sources)

    if not retrieved:
        return ScientificText(
            text="Es sind keine passenden Dokumente für dieses Thema in der Datenbank vorhanden. "
                 "Bitte laden Sie zunächst relevante wissenschaftliche Literatur hoch.",
            citations=[],
            sources=[],
            reference_list="",
        )

    # Rerank sources
    candidates = [
        RerankCandidate(
            doc_id=chunk.doc_id,
            chunk_id=chunk.chunk_id,
            content=chunk.content,
            score=chunk.score,
            meta=chunk.meta,
        )
        for chunk in retrieved
    ]
    ranked = rerank(topic, candidates)

    # Build context with citations
    context_parts = []
    citations = []

    for idx, item in enumerate(ranked[:num_sources], 1):
        meta = _extract_metadata(item)
        citation = Citation(
            doc_id=item.doc_id,
            chunk_id=item.chunk_id,
            authors=meta.get('authors'),
            year=meta.get('year'),
        )
        citations.append(citation)

        # Add context with citation placeholder
        context_parts.append(
            f"[Quelle {idx}: {citation.in_text}]\n{item.content}\n"
        )

    context = "\n".join(context_parts)

    # Generate the section
    prompt = _get_section_prompt(section, topic, context)

    # Call LLM
    if settings.llm_provider == "anthropic":
        client = _get_anthropic()
        message = client.messages.create(
            model=settings.llm_model,
            max_tokens=4000,  # Longer for scientific writing
            temperature=0.3,   # Slightly higher for more natural writing
            messages=[{"role": "user", "content": prompt}],
        )
        generated_text = "".join(
            block.text for block in message.content if hasattr(block, "text")
        )
    else:
        client = _get_openai()
        completion = client.chat.completions.create(
            model=settings.llm_model,
            temperature=0.3,
            max_tokens=4000,
            messages=[
                {"role": "system", "content": "Du bist ein wissenschaftlicher Autor."},
                {"role": "user", "content": prompt},
            ],
        )
        generated_text = completion.choices[0].message.content or ""

    # Build reference list
    reference_list = _build_harvard_references(citations)

    # Convert retrieved to RetrievedChunk for sources
    sources = [
        RetrievedChunk(
            doc_id=item.doc_id,
            chunk_id=item.chunk_id,
            content=item.content,
            score=item.score,
            meta=item.meta,
        )
        for item in ranked
    ]

    return ScientificText(
        text=generated_text,
        citations=citations,
        sources=sources,
        reference_list=reference_list,
    )


__all__ = [
    "PaperSection",
    "SECTION_NAMES_DE",
    "Citation",
    "ScientificText",
    "generate_scientific_section",
]
