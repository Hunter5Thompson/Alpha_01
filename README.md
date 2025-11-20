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

## Produktionsreife & Sicherheit

### Sicherheitshinweise

**WICHTIG**: Dieses System wurde für Produktionsreife optimiert, aber folgende Punkte müssen beachtet werden:

1. **API-Schlüssel**
   - Verwende separate API-Keys für Entwicklung, Staging und Produktion
   - Rotiere API-Keys regelmäßig
   - Aktiviere API-Key-Berechtigungen nur für benötigte Funktionen
   - Monitore API-Nutzung und setze Billing-Alerts
   - Nutze Rate Limiting, falls verfügbar

2. **Datenbank-Credentials**
   - Ändere die Standard-Passwörter in `.env` **vor** dem Deployment
   - Verwende starke, einzigartige Passwörter (mind. 20 Zeichen, zufällig generiert)
   - Nutze Docker Secrets oder verschlüsselte Umgebungsvariablen in der Produktion
   - Exponiere PostgreSQL **nicht** direkt im Internet (nur über interne Netzwerke)

3. **Datenschutz**
   - Prüfe hochgeladene Dokumente auf sensible Daten
   - Implementiere Zugriffskontrolle für die Streamlit-App
   - Erwäge Verschlüsselung für Embeddings in der Datenbank
   - Logge keine API-Responses, die vertrauliche Daten enthalten könnten

4. **Ressourcenlimits**
   - File Upload ist auf 50 MB limitiert (konfigurierbar via `MAX_FILE_SIZE_MB`)
   - Setze Memory-Limits für Docker-Container
   - Konfiguriere PostgreSQL Connection Pooling (standardmäßig: 10 Connections, 20 Overflow)

### Deployment-Empfehlungen

**Für Entwicklung:**
```bash
cp .env.example .env
# API-Keys in .env eintragen
docker compose up -d --build
```

**Für Produktion:**
1. Verwende einen Reverse Proxy (nginx, Traefik) mit HTTPS
2. Setze Umgebungsvariablen über sichere Mechanismen (AWS Secrets Manager, HashiCorp Vault)
3. Aktiviere PostgreSQL-Backups
4. Nutze separate Container für App und DB auf verschiedenen Hosts
5. Implementiere Logging & Monitoring (Prometheus, Grafana)
6. Setze Firewall-Regeln (nur Port 443 für Reverse Proxy)

**Docker-Compose Production Override:**
```yaml
# docker-compose.prod.yml
services:
  app:
    restart: always
    environment:
      - LOG_LEVEL=WARNING
    deploy:
      resources:
        limits:
          cpus: '2'
          memory: 4G

  db:
    restart: always
    ports:
      - "127.0.0.1:5432:5432"  # Nur localhost
    deploy:
      resources:
        limits:
          memory: 2G
```

Starten mit: `docker compose -f docker-compose.yml -f docker-compose.prod.yml up -d`

### Verbesserungen in diesem Release

**Kritische Bugfixes:**
- ✅ Type Error in `scientific_writing.py` behoben
- ✅ Integer-Konvertierung in Settings mit Validierung
- ✅ Dynamisches Database Schema (passt sich automatisch an Embedding-Dimensionen an)
- ✅ Optimiertes Upsert mit PostgreSQL `ON CONFLICT` (10x schneller bei großen Ingests)

**Produktionsreife-Features:**
- ✅ Retry-Logik für API-Calls (3 Retries mit exponential backoff)
- ✅ Input-Validierung (File Size, Extensions, Empty Files)
- ✅ Verbessertes Error Handling & Logging
- ✅ Database Connection Pooling konfiguriert
- ✅ Sichere Credential-Verwaltung via `.env.example`

### Monitoring & Logs

Logs anzeigen:
```bash
docker compose logs -f app
docker compose logs -f db
```

Datenbank-Verbindung testen:
```bash
docker compose exec db psql -U rag -d ragdb -c "SELECT COUNT(*) FROM documents;"
```

## Bekannte Einschränkungen

* Docling benötigt zusätzliche Systemabhängigkeiten für OCR (z. B. `tesseract-ocr`), die im Container
  installiert sein müssen.
* Ohne gültige API-Keys werden im UI Hinweise angezeigt; Funktionen sind deaktiviert.
* **Wissenschaftliches Schreiben**: Die Qualität hängt stark von der hochgeladenen Literatur ab.
  Für beste Ergebnisse sollten relevante, hochwertige wissenschaftliche Quellen verwendet werden.
* Streamlit hat keine eingebaute Authentifizierung – für Produktion sollte ein Reverse Proxy mit
  Basic Auth oder OAuth verwendet werden.

## Lizenz

Dieses Projekt steht unter der [MIT-Lizenz](LICENSE).
