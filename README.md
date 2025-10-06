# Codex – Agentisches RAG-System

Codex ist ein containerisiertes Retrieval-Augmented-Generation-System (RAG), das heterogene
Dokumente via [Docling](https://github.com/docling-project/docling) in Markdown konvertiert, mit
OpenAI-Embeddings indiziert und Antworten über Anthropic oder OpenAI generiert. Eine minimale
Streamlit-Oberfläche erlaubt das Hochladen von Dokumenten, das Starten der Ingestion und das Stellen
von Fragen mit Quellenangaben.

## Architektur

```
┌────────┐     ┌──────────────────────┐     ┌──────────────┐
│Upload  │ ─▶ │ Docling → Chunking   │ ─▶ │ OpenAI Emb.  │
└────────┘     └──────────────────────┘     └──────┬───────┘
                                                    │
                                           ┌────────▼────────┐
                                           │ Postgres +       │
                                           │ pgvector         │
                                           └────────┬────────┘
                                                    │
                                           ┌────────▼────────┐
                                           │ Retrieval +      │
                                           │ Reranker         │
                                           └────────┬────────┘
                                                    │
                                           ┌────────▼────────┐
                                           │ LLM (Anthropic/  │
                                           │ OpenAI)          │
                                           └──────────────────┘
```

## Schnellstart

1. **Repo vorbereiten**

   ```bash
   cp .env.example .env
   # In .env die API-Keys für OpenAI und Anthropic hinterlegen
   ```

2. **Stack starten**

   ```bash
   docker compose up -d --build
   ```

3. **Weboberfläche öffnen** – [http://localhost:8501](http://localhost:8501)

4. **Dokumente hochladen** und „Ingest starten“ klicken. Anschließend Fragen im unteren Bereich
   stellen. Quellen werden im Expander angezeigt.

### Datenablage

* Lokale Dokumente werden unter `./data` gespeichert und in den App-Container gemountet.
* Beim ersten Start werden – falls `AUTO_INGEST=true` und die Datenbank leer ist – alle Dateien aus
  `/data` automatisch ingestiert.

### Datenbank

* Postgres 16 mit `pgvector`.
* Tabelle `documents` speichert Markdown-Chunks inkl. Embedding und Metadaten.
* IVFFlat Index (Cosine) beschleunigt die Ähnlichkeitssuche.

## Module

* `rag_agent/app.py` – Streamlit-GUI.
* `rag_agent/ingest.py` – Upload, Docling-Konvertierung, Chunking, Embedding.
* `rag_agent/embeddings.py` – OpenAI Embedding-Client.
* `rag_agent/rerank.py` – LLM-basierter Reranker (OpenAI).
* `rag_agent/qa.py` – End-to-End-Pipeline für Fragen.
* `rag_agent/llm.py` – Antwortgenerierung via Anthropic/OpenAI.
* `rag_agent/storage.py` – SQLAlchemy-Modelle & Persistence.
* `rag_agent/cli.py` – Auto-Ingest beim Container-Start.

## Tests & Entwicklung

* Lokale Entwicklung ohne Container ist möglich:

  ```bash
  python -m venv .venv && source .venv/bin/activate
  pip install -r requirements.txt
  streamlit run rag_agent/app.py
  ```

* Für lokale Tests empfiehlt sich eine Postgres-Instanz mit pgvector (z. B. via Docker).

## Bekannte Einschränkungen

* Die Datenbank-Tabelle ist auf Embeddings mit 3072 Dimensionen ausgelegt (`text-embedding-3-large`).
  Für andere Modelle muss die Spalte `embedding` angepasst und re-ingestiert werden.
* Docling muss im Container installiert sein (wird über `requirements.txt` erledigt), benötigt aber
  zusätzliche Systemabhängigkeiten für OCR (z. B. `tesseract-ocr`).
* Ohne gültige API-Keys werden im UI Hinweise angezeigt; Funktionen sind deaktiviert.

## Lizenz

Dieses Projekt steht unter der [MIT-Lizenz](LICENSE).
