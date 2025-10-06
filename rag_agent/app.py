"""Streamlit front-end for Codex RAG."""
from __future__ import annotations

import logging
from pathlib import Path
from typing import List, Any

import streamlit as st

from .ingest import ingest_paths, secure_filename
from .qa import answer_question
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

    st.title("Codex – Dokumente fragen, Antworten erhalten")
    st.caption("Agentisches RAG-System mit Docling, OpenAI und Anthropic")

    _status_messages()

    st.subheader("Daten importieren")
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

    st.subheader("Frage beantworten")
    question = st.text_area("Deine Frage an die Dokumente", height=120)
    if st.button("Antwort anzeigen"):
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

    st.caption("Fehlermeldungen? Bitte API-Keys prüfen und Logs ansehen.")


if __name__ == "__main__":  # pragma: no cover
    main()
