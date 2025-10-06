#!/usr/bin/env bash
set -euo pipefail

export STREAMLIT_SERVER_PORT="8501"
export STREAMLIT_SERVER_ADDRESS="0.0.0.0"
export PYTHONUNBUFFERED=1

python - <<'PY'
from rag_agent.cli import auto_ingest

try:
    auto_ingest()
except Exception as exc:  # pragma: no cover
    import logging

    logging.basicConfig(level="INFO")
    logging.exception("Auto-Ingest fehlgeschlagen: %s", exc)
PY

exec streamlit run rag_agent/app.py
