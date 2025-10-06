"""Command-line helpers for automation."""
from __future__ import annotations

import logging

from .ingest import ingest_data_directory
from .settings import settings
from .storage import chunk_count, init_db

logger = logging.getLogger(__name__)


def auto_ingest() -> None:
    init_db()
    if not settings.auto_ingest:
        logger.info("Auto-Ingest deaktiviert.")
        return
    if chunk_count() > 0:
        logger.info("Bereits Daten vorhanden – Auto-Ingest übersprungen.")
        return
    results = ingest_data_directory()
    logger.info("Auto-Ingest abgeschlossen: %s Dateien", len(results))


__all__ = ["auto_ingest"]
