# Codex — Product Requirements Document (PRD)

**Version:** 1.0
**Date:** 2025-10-06
**Owner:** Rob (AI Engineer)
**Author:** Assistant (GPT-5 Thinking)

---

## 1. Summary

Codex ist ein **agentisches RAG**-System als **SaaS im Container**. Endnutzer benötigen ausschließlich **Docker**. Das System wandelt heterogene Dokumente (PDF, DOCX, PPTX, HTML, Bilder) via **Docling** in **Markdown**, führt **Chunking**, **OpenAI-Embeddings**, **pgvector**-Speicherung und **k-NN Retrieval** durch. Optional wird ein **LLM-basierter Re-Ranker** (OpenAI) verwendet, bevor die Antwort von **Anthropic (Claude)** oder **OpenAI** generiert wird. Eine **ultra-minimale Streamlit-GUI** erlaubt: Dokumente importieren, ingestieren, Fragen stellen, Antworten + Quellen sehen. Keine lokalen Modelle, kein n8n, kein Ollama.

---

## 2. Goals & Non-Goals

### 2.1 Goals

* **Zero-Install UX**: Nutzer braucht nur Docker (Desktop/Engine).
* **Einfachste GUI**: Ein Eingabefeld + Button; transparente Quellenanzeige; Upload & Ingest in der GUI.
* **Breite Dateiformat-Unterstützung**: PDF, DOCX, PPTX, HTML, PNG/JPG, MD/TXT → **Docling → Markdown**.
* **Sichere, reproduzierbare Speicherung**: pgvector mit Cosine-KNN, idempotenter Ingest.
* **API-only KI**: Embeddings, Reranker, LLM ausschließlich via **OpenAI/Anthropic**.
* **Plattformübergreifend**: Linux/macOS/Windows via Docker Compose.
* **Kostentransparenz**: Reranker/Top-k intern steuerbar; Standard ökonomisch.

### 2.2 Non-Goals

* Kein Finetuning von LLMs.
* Kein Self-Hosted LLM (kein Ollama).
* Keine Orchestrierung via n8n im MVP.
* Keine komplexe Admin-UI (nur Minimal-GUI für Endnutzer).

---

## 3. Personas

* **Endnutzer (Knowledge Worker)**: Möchte Dateien droppen, Fragen stellen, Antworten erhalten. Kein technisches Setup.
* **Ops/IT**: Startet/überwacht Container, setzt API-Keys, Backups.
* **AI Engineer (Rob)**: Konfiguriert Default-Parameter (k, Reranker), deployed Images/Compose, beobachtet Kosten/Qualität.

---

## 4. User Stories

1. *Als Endnutzer* möchte ich **Dateien per Upload** in der Weboberfläche hinzufügen, damit ich direkt danach Fragen stellen kann.
2. *Als Endnutzer* möchte ich bei leerer Datenbank einen **klaren Hinweis** statt eines Fehlers sehen.
3. *Als Endnutzer* möchte ich **eine Frage eingeben** und eine **konzise Antwort mit Quellen** bekommen.
4. *Als Ops* möchte ich das System mit **einem Befehl** starten (Docker Compose) und nur eine **.env** pflegen.
5. *Als AI Engineer* möchte ich **Parametrisierung** (Modellauswahl, k, Reranker-Modelle) via **.env** ohne UI-Chaos.

**Akzeptanzkriterien pro Story** siehe Abschnitt 14.

---

## 5. Scope (MVP)

* **Ingestion**

  * Datei-Discovery: Upload (GUI) und Batch aus `./data`.
  * **Docling → Markdown** für: PDF, DOCX, PPTX, HTML, PNG/JPG, MD/TXT.
  * **Chunking**: satzbasiert + Greedy Merge, Ziel ~220 Tokens, Overlap ~40 (env-konfigurierbar).
  * **Embeddings**: OpenAI `text-embedding-3-*` (Default: `large`, 3072-D).
  * Speicherung: Tabelle `documents` (pgvector), idempotent via UNIQUE(doc_id, chunk_id).

* **Retrieval**

  * k-NN Cosine auf `embedding` (IVFFlat Index).
  * Optionales Hybrid (FTS Preselect) – im MVP **aus**, aber technisch vorhanden.
  * Optionaler **Reranker** über OpenAI (LLM-Scoring) – **an** im MVP.

* **Answering**

  * LLM Provider: **Anthropic** (Claude) **oder** **OpenAI**.
  * Prompting: „Nutze nur Kontext, antworte knapp (DE), zitiere [doc_id#chunk_id]“.

* **GUI (Streamlit)**

  * **Upload** + **Ingest starten** (Button).
  * **Fragefeld** + **Antwort** + **Quellen (Expander)**.
  * **Hinweise statt Fehler** (fehlende Keys, leere DB, Netzwerkfehler).

* **Deployment**

  * **Docker Compose**: `db (pgvector)`, `app (Streamlit)`; optional separater `ingest`-Job, aber GUI kann ingestieren.
  * **Auto-Ingest** beim Erststart, wenn `/data` Inhalte hat (abschaltbar via env).

---

## 6. Out of Scope (MVP)

* Multi-Tenant-Auth/SSO, Rollen/Rechte.
* Deduplizierte globale Wissensgraphen, Cross-Doc Linkage.
* Vollständige Admin-Konsole (nur Logs + einfache Hinweise).
* Kosten-Dashboards im UI (nur Logging/Tracing vorgesehen).

---

## 7. UX & Content Design

* **Startseite**: Titel, kurzer Untertitel.
* **Status-Hinweise** (Cards/Banner):

  * „API-Keys fehlen“ (Fehler)
  * „Noch keine Inhalte indexiert – bitte Daten importieren“ (Info)
* **Sektion „Daten importieren“**:

  * File Uploader (Mehrfach).
  * Button **„Ingest starten“** → Spinner → Erfolg/Fehler-Toast.
* **Frage/Antwort**:

  * Eingabefeld „Deine Frage an die Dokumente“.
  * Button „Antwort anzeigen“.
  * Antwort (Markdown-Rendering).
  * Expander „Verwendete Quellen“ (standardmäßig geöffnet).
* **Keine** Experten-Schieberegler im MVP.

**Fehlertexte**: Klar, deutsch, lösungsorientiert („Bitte API-Keys setzen…“).

---

## 8. Functional Requirements

1. **Upload**: Akzeptiert `.pdf, .docx, .pptx, .html, .htm, .png, .jpg, .jpeg, .md, .txt`; speichert unter `/data` mit UUID-Präfix.
2. **Docling-Konvertierung**: Jede Datei → Markdown-String.
3. **Chunking**: Parametrisierbar (`MAX_TOKENS`, `OVERLAP_TOKENS`), Default 220/40.
4. **Embedding**: OpenAI `text-embedding-3-*`; Fehlerbehandlung bei Rate Limits/Netz.
5. **Storage**: Upsert in `documents` (UNIQUE `doc_id, chunk_id`).
6. **Retrieval**: k-NN (k=8 Default), Cosine; optional Hybrid-FTS (aus).
7. **Rerank**: OpenAI LLM-Scoring (JSON-Resultate robust geparst).
8. **Answering**: LLM (Anthropic/OpenAI), temperaturarm, Zitate `[doc_id#chunk_id]`.
9. **GUI-Stabilität**: Keine Abstürze bei leerer DB/fehlenden Keys.
10. **Auto-Ingest**: Beim App-Start, wenn DB leer **und** `/data` gefüllt (abschaltbar).

---

## 9. Non-Functional Requirements

* **Portabilität**: Alles in Containern; einzig Docker als Voraussetzung.
* **Sicherheit**: Non-root-User im App-Container; Upload-Dateinamen gehärtet; API-Keys nur via `.env`.
* **Performance**: Ingest linear zur Größe; Retrieval < 1s bei n≲100k Chunks (Index abhängig); Rerank top-k ≤ 8.
* **Kostenkontrolle**: Standardmäßig `gpt-4o-mini` (Rerank), begrenzte `max_tokens`.
* **Observability**: Structured Logging, einfache Metriken (Ingest: #files/#chunks).
* **Reliability**: Healthcheck DB; App startet trotz leerer DB.

---

## 10. System Architecture

* **Frontend**: Streamlit (minimal).
* **Backend**: In-App Python-Module (Ingest/Retrieval/Answer).
* **DB**: Postgres 16 + pgvector Extension (IVFFlat).
* **External APIs**: OpenAI (Embeddings + Rerank), Anthropic/OpenAI (LLM).
* **Containers**: `db`, `app` (+ optional `ingest` Job).

**Flow**: Upload → Docling→Markdown → Chunking → Embeddings (OpenAI) → `documents` (pgvector) → Retrieval (kNN) → optional Rerank (OpenAI) → Answer (Anthropic/OpenAI) → GUI.

---

## 11. API/Integration Contracts (Internal)

* **Embedding**: OpenAI `embeddings.create(model, input=[...])` → `embedding: float[]` (3072/1536).
* **Reranking**: OpenAI ChatCompletion mit striktem JSON-Output (Rerank-Liste).
* **Answering**:

  * Anthropic Messages API: `messages.create(model, messages=[{role:user, content:prompt}], max_tokens, temperature)`
  * OpenAI Chat Completions API: analog.

**Timeouts/Retry**: Exponentielles Backoff bei Transienten (HTTP 429/5xx).

---

## 12. Data Model & Storage

### 12.1 Table `documents`

* `id BIGSERIAL PK`
* `doc_id TEXT NOT NULL` (Dateiname/Quelle)
* `chunk_id INT NOT NULL`
* `content TEXT NOT NULL`
* `embedding VECTOR(3072)` (bei `text-embedding-3-large`)
* `meta JSONB DEFAULT '{}'`

**Indices**:

* `UNIQUE(doc_id, chunk_id)`
* `IVFFlat` auf `embedding` **(vector_cosine_ops, lists=100)**
* optional `GIN` auf `to_tsvector('simple', content)`

**Migration bei Modellwechsel** (z. B. 3072→1536): Neue Tabelle mit passender Dimension; Re-Ingest.

---

## 13. Configuration (.env)

* `DATABASE_URL=postgresql+psycopg://rag:ragpass@db:5432/ragdb`
* `OPENAI_API_KEY=...`
* `OPENAI_EMBED_MODEL=text-embedding-3-large`
* `LLM_PROVIDER=anthropic|openai`

* `LLM_MODEL=claude-3-7-sonnet-20250219|gpt-4o-mini|…`
* `RERANK_PROVIDER=openai`
* `RERANK_MODEL=gpt-4o-mini`
* `AUTO_INGEST=true`
* `MAX_TOKENS=220` / `OVERLAP_TOKENS=40` (optional)

---

## 14. Acceptance Criteria

* **AC1**: Mit nur Docker & `.env` (mit gültigen Keys) startet `docker compose up -d` den Stack; `http://localhost:8501` ist erreichbar.
* **AC2**: Bei leerer DB zeigt die GUI **Info-Hinweis** statt Fehler; Upload + Ingest funktionieren.
* **AC3**: Upload akzeptiert alle spezifizierten Formate; Dateien werden im Container unter `/data` abgelegt.
* **AC4**: „Ingest starten“ verarbeitet Dateien mit Docling → erzeugt Chunks → speichert Embeddings in `documents` (sichtbar via COUNT > 0).
* **AC5**: Nutzer kann eine Frage stellen und erhält eine **relevante, knappe Antwort** mit **Quellen-Expander**.
* **AC6**: System bleibt responsiv bei 10k+ Chunks; Antwortzeit < 3s (ohne API-Latenzspitzen).
* **AC7**: Fehlende API-Keys werden als **Meldung** angezeigt; keine ungefangenen Exceptions im UI.

---

## 15. Security & Compliance

* App-Container läuft als **non-root**.
* Upload-Filenames: **UUID-Präfix**, keine Pfadübernahme.
* Secrets nur in `.env` (nicht im Image).
* DB-User-Trennung (optional): `app_read` (SELECT), `ingest_write` (INSERT).
* Prompt-Härtung: „Nur Kontext verwenden“, Zitatpflicht.

---

## 16. Performance & Capacity

* **RAG Retrieval**: IVFFlat `lists` tunable; Standard 100.
* **k (candidate set)**: 8 (MVP), intern anpassbar.
* **Rerank**: Top-N ≤ 5; Modell `gpt-4o-mini`.
* **Batching**: Embeddings in Batches (SDK-seitig).
* **Caches**: optional LRU für (query, chunk_id) Scores – Post-MVP.

---

## 17. Observability & Operations

* **Structured Logging** (app, ingest, storage).
* **DB Healthcheck** (Compose).
* **Metrics (basic)**: Ingest-Statistik (#files, #chunks).
* **Backups**: Postgres-Volume `pgdata` (Ops-Verantwortung).

---

## 18. Risks & Mitigations

* **API-Limits/Kosten**: Rate Limits → Retry/Backoff; kleineres Modell für Rerank.
* **PDF-OCR/Qualität**: Docling-Edgecases → Post-Processing (Dedup); manuelle Korrektur möglich.
* **Embedding-Dimension Drift**: Falsches Schema → klar dokumentierte Migration.
* **Corporate Proxy**: Env `HTTP(S)_PROXY` unterstützen.

---

## 19. Timeline & Milestones (MVP)

* **Woche 1**: Container-Basis, DB-Init, Embedding/Retrieval, Minimal-GUI.
* **Woche 2**: Docling-Ingest, Upload-Flow, Reranker, Fehlertexte.
* **Woche 3**: Hardening, Load-Test, Doku, Release-Kandidat v1.0.

---

## 20. Open Questions

* Benötigen wir **Hybrid-Suche** (FTS+Vektor) bereits aktiv im MVP?
* Sollen wir im UI einen **„Re-Index“-Knopf** (Neuaufbau Embeddings) anbieten?
* Welche **Modell-Defaults** für Produktionskunden (Kosten/Qualität)?

---

## 21. Glossar (Projekt-spezifisch)

* **Docling**: Konvertiert heterogene Dokumente in strukturierte Markdown/JSON-Repräsentationen.
* **RAG**: Retrieval-Augmented Generation; Antworten werden durch vorherige Dokument-Retrievals gestützt.
* **pgvector**: Postgres-Extension, speichert Vektoren, unterstützt Vektor-Indexe/Ähnlichkeitssuche.
* **IVFFlat**: Annäherungsindex für Vektor-KNN.
* **Re-Ranker**: Zweite Stufe, die Top-k-Kandidaten fein sortiert (hier via OpenAI LLM-Scoring).

---

## 22. Deliverables (Artefakte)

* `docker-compose.yml` (db + app).
* `docker/db/init/*.sql` (Extension + Schema + Indizes).
* App-Code (`rag_agent/…`):

  * `app.py` (GUI), `ingest.py` (Docling → Markdown → Chunking → Embedding → DB),
  * `agents.py`, `embeddings.py`, `rerank.py`, `llm.py`, `storage.py`, `chunking.py`, `schemas.py`, `settings.py`.
* `docker/app/Dockerfile`, `docker/app/entrypoint.sh` (mit Auto-Ingest).
* `.env.example` mit Defaults.
* README (Quickstart).

---

## 23. Acceptance Test Plan (High-Level)

1. **Cold Start**: Frische Volumes, `.env` mit API-Keys → `docker compose up -d` → UI erreichbar, leerer DB-Hinweis.
2. **Upload & Ingest**: PDF + DOCX hochladen → „Ingest starten“ → Erfolgsmeldung; DB COUNT > 0.
3. **Q&A**: Frage mit Antwort + Quellen.
4. **Fehlende Keys**: Entferne Keys → UI zeigt Hinweis, kein Absturz.
5. **Große Datei**: >50 Seiten PDF → Ingest dauert, UI blockiert nicht; Query danach schnell.

---
