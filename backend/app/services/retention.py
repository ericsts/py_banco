import asyncio
import logging
from datetime import datetime, timedelta, timezone

from ..config import settings
from ..db import SessionLocal
from ..models import DocType, SourceFile
from .importer import purge_pdf

logger = logging.getLogger("retention")

CHECK_INTERVAL_SECONDS = 6 * 3600


def run_retention_once() -> int:
    """Apaga (do disco) o PDF de arquivos reconhecidos e já importados há
    mais de RETENTION_DAYS. Arquivos em quarentena (não reconhecidos) ficam
    isentos até serem resolvidos manualmente."""
    cutoff = datetime.now(timezone.utc) - timedelta(days=settings.retention_days)
    db = SessionLocal()
    purged = 0
    try:
        candidates = (
            db.query(SourceFile)
            .filter(
                SourceFile.stored_path.is_not(None),
                SourceFile.doc_type != DocType.unsupported,
                SourceFile.uploaded_at.is_not(None),
                SourceFile.uploaded_at < cutoff,
            )
            .all()
        )
        for sf in candidates:
            purge_pdf(sf)
            purged += 1
        db.commit()
    finally:
        db.close()
    return purged


async def retention_loop() -> None:
    while True:
        try:
            n = run_retention_once()
            if n:
                logger.info("Retenção: %d PDF(s) purgado(s)", n)
        except Exception:
            logger.exception("Falha na rotina de retenção")
        await asyncio.sleep(CHECK_INTERVAL_SECONDS)
