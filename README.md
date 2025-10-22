# Codex – Agentisches RAG-System & Wissenschaftliches Schreiben

Codex ist ein containerisiertes Retrieval-Augmented-Generation-System (RAG), das heterogene
Dokumente via [Docling](https://github.com/docling-project/docling) in Markdown konvertiert, mit
OpenAI-Embeddings indiziert und Antworten über Anthropic oder OpenAI generiert.

**Neu: Wissenschaftlicher Schreib-Bot** – Generiere automatisch wissenschaftliche Paper-Sektionen
(Abstract, Einleitung, Literaturübersicht, Methodik, Ergebnisse, Diskussion, Schlussfolgerung)
mit korrekten **Harvard-Zitationen** basierend auf deiner hochgeladenen Literatur.

Eine minimale Streamlit-Oberfläche bietet zwei Modi:
- **Q&A-Modus**: Stelle Fragen an deine Dokumente
- **Wissenschaftliches Schreiben**: Generiere Paper-Sektionen mit automatischen Zitationen

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

4. **Dokumente hochladen** und „Ingest starten" klicken.

5. **Q&A-Modus**: Stelle Fragen an deine Dokumente. Quellen werden mit Scores angezeigt.

6. **Wissenschaftliches Schreiben**: Wähle eine Paper-Sektion (z.B. "Einleitung"), gib dein
   Forschungsthema ein und generiere einen wissenschaftlichen Text mit Harvard-Zitationen.

### Datenablage

* Lokale Dokumente werden unter `./data` gespeichert und in den App-Container gemountet.
* Beim ersten Start werden – falls `AUTO_INGEST=true` und die Datenbank leer ist – alle Dateien aus
  `/data` automatisch ingestiert.

### Datenbank

* Postgres 16 mit `pgvector`.
* Tabelle `documents` speichert Markdown-Chunks inkl. Embedding und Metadaten.
* IVFFlat Index (Cosine) beschleunigt die Ähnlichkeitssuche.

## Module

* `rag_agent/app.py` – Streamlit-GUI mit Q&A und wissenschaftlichem Schreiben.
* `rag_agent/scientific_writing.py` – **NEU**: Wissenschaftlicher Schreib-Bot mit Harvard-Zitationen.
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

## Wissenschaftliches Schreiben

Der neue wissenschaftliche Schreib-Modus bietet:

### Verfügbare Paper-Sektionen
* **Abstract/Zusammenfassung** (150-250 Wörter)
* **Einleitung** – Hintergrund, Forschungsfrage, Zielsetzung
* **Literaturübersicht** – Systematischer Überblick über den Forschungsstand
* **Methodik** – Detaillierte Beschreibung des methodischen Vorgehens
* **Ergebnisse** – Objektive Präsentation der Befunde
* **Diskussion** – Interpretation und Einordnung der Ergebnisse
* **Schlussfolgerung** – Zusammenfassung und Ausblick

### Features
* **Harvard-Zitierstil**: Automatische In-Text-Zitationen (Autor, Jahr) und Literaturverzeichnis
* **Quellenbasiert**: Alle Aussagen werden durch hochgeladene Dokumente gestützt
* **Wissenschaftlicher Stil**: Objektive, präzise Formulierungen mit Fachterminologie
* **Anpassbar**: Wähle die Anzahl der Quellen (3-15) für jeden generierten Text
* **Deutsche Sprache**: Alle Texte werden auf Deutsch generiert

### Workflow
1. Lade wissenschaftliche Literatur hoch (PDF, DOCX, etc.)
2. Wähle die gewünschte Paper-Sektion
3. Gib dein Forschungsthema oder deine Fragestellung ein
4. Der Bot generiert einen strukturierten wissenschaftlichen Text
5. Erhalte automatisch ein Harvard-Literaturverzeichnis

## Bekannte Einschränkungen

* Die Datenbank-Tabelle ist auf Embeddings mit 3072 Dimensionen ausgelegt (`text-embedding-3-large`).
  Für andere Modelle muss die Spalte `embedding` angepasst und re-ingestiert werden.
* Docling muss im Container installiert sein (wird über `requirements.txt` erledigt), benötigt aber
  zusätzliche Systemabhängigkeiten für OCR (z. B. `tesseract-ocr`).
* Ohne gültige API-Keys werden im UI Hinweise angezeigt; Funktionen sind deaktiviert.
* **Wissenschaftliches Schreiben**: Die Qualität hängt stark von der hochgeladenen Literatur ab.
  Für beste Ergebnisse sollten relevante, hochwertige wissenschaftliche Quellen verwendet werden.

## Lizenz

Dieses Projekt steht unter der [MIT-Lizenz](LICENSE).
