"""Streamlit front-end for Codex RAG."""
from __future__ import annotations

import logging
from pathlib import Path
from typing import List, Any

import streamlit as st

from .ingest import ingest_paths, secure_filename
from .qa import answer_question
from .scientific_writing import (
    PaperSection,
    SECTION_NAMES_DE,
    generate_scientific_section,
)
from .settings import settings
from .storage import chunk_count, init_db

logger = logging.getLogger(__name__)


def _status_messages() -> None:
    if not settings.has_embedding_credentials:
        st.error("OPENAI_API_KEY fehlt – bitte in der .env setzen.")
    if not settings.has_llm_credentials:
        st.error("LLM-API-Key fehlt – bitte konfigurieren.")
    if chunk_count() == 0:
        st.info("Noch keine Inhalte indexiert – bitte Dokumente ingestieren.")


def _save_uploaded_files(files: List[Any]) -> List[Path]:
    saved_paths: List[Path] = []
    data_dir = Path(settings.data_dir)
    data_dir.mkdir(parents=True, exist_ok=True)
    for uploaded in files:
        filename = secure_filename(uploaded.name)
        destination = data_dir / filename
        destination.write_bytes(uploaded.getvalue())
        saved_paths.append(destination)
    return saved_paths


def main() -> None:
    st.set_page_config(page_title="Codex", layout="wide")
    init_db()

    st.title("Codex – RAG-System & Wissenschaftliches Schreiben")
    st.caption("Agentisches RAG-System mit Docling, OpenAI und Anthropic")

    _status_messages()

    # Mode selection
    mode = st.radio(
        "Modus auswählen:",
        ["📚 Q&A: Fragen beantworten", "✍️ Wissenschaftliches Schreiben"],
        horizontal=True,
    )

    st.divider()

    # Data import section (shared by both modes)
    with st.expander("📤 Daten importieren", expanded=(chunk_count() == 0)):
        uploaded_files = st.file_uploader(
            "Unterstützte Formate: PDF, DOCX, PPTX, HTML, PNG/JPG, MD/TXT",
            accept_multiple_files=True,
        )

        if st.button("Ingest starten"):
            if not uploaded_files:
                st.warning("Bitte zuerst Dateien hochladen.")
            else:
                with st.spinner("Ingestion läuft…"):
                    paths = _save_uploaded_files(uploaded_files)
                    results = ingest_paths(paths)
                if results:
                    chunk_total = sum(result.chunks for result in results)
                    st.success(f"Ingest abgeschlossen ({chunk_total} Chunks).")
                else:
                    st.error("Ingest fehlgeschlagen – Details siehe Logs.")

    st.divider()

    # Q&A Mode
    if mode == "📚 Q&A: Fragen beantworten":
        st.subheader("Frage beantworten")
        question = st.text_area("Deine Frage an die Dokumente", height=120)
        if st.button("Antwort anzeigen", type="primary"):
            if not question.strip():
                st.warning("Bitte eine Frage eingeben.")
            else:
                with st.spinner("Suche nach Antworten…"):
                    try:
                        result = answer_question(question)
                    except Exception as exc:  # pragma: no cover - UI feedback
                        st.error(f"Fehler bei der Antwortgenerierung: {exc}")
                    else:
                        st.markdown(result.text)
                        with st.expander("Verwendete Quellen", expanded=True):
                            for source in result.sources:
                                st.markdown(
                                    f"**{source.doc_id}#{source.chunk_id}** – Score: {source.score:.2f}\n\n{source.content}"
                                )

    # Scientific Writing Mode
    else:
        st.subheader("✍️ Wissenschaftliches Schreiben")
        st.markdown(
            "Generiere wissenschaftliche Texte mit automatischen Zitationen im **Harvard-Stil** "
            "basierend auf deinen hochgeladenen Dokumenten."
        )

        col1, col2 = st.columns([2, 1])

        with col1:
            topic = st.text_area(
                "Forschungsthema / Fragestellung",
                height=100,
                placeholder="z.B. 'Die Auswirkungen von maschinellem Lernen auf die medizinische Diagnostik'",
            )

        with col2:
            section = st.selectbox(
                "Paper-Sektion",
                options=list(PaperSection),
                format_func=lambda x: SECTION_NAMES_DE[x],
            )

            num_sources = st.slider(
                "Anzahl Quellen",
                min_value=3,
                max_value=15,
                value=8,
                help="Wie viele Quellen sollen für die Textgenerierung verwendet werden?",
            )

        if st.button("Text generieren", type="primary"):
            if not topic.strip():
                st.warning("Bitte ein Forschungsthema eingeben.")
            elif chunk_count() == 0:
                st.error("Keine Dokumente in der Datenbank. Bitte zuerst Literatur hochladen.")
            else:
                with st.spinner(f"Generiere {SECTION_NAMES_DE[section]}…"):
                    try:
                        result = generate_scientific_section(
                            section=section,
                            topic=topic,
                            num_sources=num_sources,
                        )
                    except Exception as exc:  # pragma: no cover - UI feedback
                        st.error(f"Fehler bei der Textgenerierung: {exc}")
                        logger.exception("Scientific writing generation failed")
                    else:
                        # Display generated text
                        st.markdown("### Generierter Text")
                        st.markdown(result.text)

                        # Display reference list
                        if result.reference_list:
                            st.markdown(result.reference_list)

                        # Display sources
                        with st.expander("📚 Verwendete Quellen", expanded=False):
                            for idx, source in enumerate(result.sources, 1):
                                st.markdown(
                                    f"**Quelle {idx}: {source.doc_id}#{source.chunk_id}** "
                                    f"(Score: {source.score:.2f})"
                                )
                                st.text(source.content[:300] + "..." if len(source.content) > 300 else source.content)
                                st.divider()

        # Help section
        with st.expander("ℹ️ Hilfe zum wissenschaftlichen Schreiben"):
            st.markdown("""
            **So funktioniert's:**

            1. **Dokumente hochladen**: Laden Sie wissenschaftliche Literatur (PDFs, DOCX, etc.) hoch
            2. **Sektion wählen**: Wählen Sie den gewünschten Abschnitt Ihres Papers
            3. **Thema eingeben**: Beschreiben Sie Ihre Forschungsfrage oder Ihr Thema
            4. **Text generieren**: Der Bot erstellt einen wissenschaftlichen Text mit Harvard-Zitationen

            **Verfügbare Sektionen:**
            - **Abstract**: Prägnante Zusammenfassung (150-250 Wörter)
            - **Einleitung**: Hintergrund, Forschungsfrage, Zielsetzung
            - **Literaturübersicht**: Systematischer Überblick über Forschungsstand
            - **Methodik**: Detaillierte Beschreibung des methodischen Vorgehens
            - **Ergebnisse**: Objektive Präsentation der Befunde
            - **Diskussion**: Interpretation und Einordnung der Ergebnisse
            - **Schlussfolgerung**: Zusammenfassung und Ausblick

            **Zitierstil**: Alle Quellen werden automatisch im **Harvard-Stil** zitiert.
            """)

    st.divider()
    st.caption("Fehlermeldungen? Bitte API-Keys prüfen und Logs ansehen.")


if __name__ == "__main__":  # pragma: no cover
    main()
