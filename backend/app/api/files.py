from fastapi import APIRouter, Depends, File, HTTPException, Query, UploadFile
from sqlalchemy.orm import Session, joinedload

from ..auth import require_admin, require_approved_user
from ..db import get_db
from ..models import ImportStatus, SourceFile, User, UserRole
from ..schemas import FileEntry, ImportResult
from ..services.importer import import_source_file, purge_pdf, save_upload

router = APIRouter(prefix="/api/files", tags=["files"])

MAX_UPLOAD_BYTES = 20 * 1024 * 1024


_STATUS_MAP = {
    ImportStatus.pending: "not_imported",
    ImportStatus.ok: "imported",
    ImportStatus.error: "error",
}


def _to_entry(sf: SourceFile, owner_email: str | None = None) -> FileEntry:
    status = "unsupported" if sf.doc_type.value == "unsupported" else _STATUS_MAP[sf.last_status]

    return FileEntry(
        id=sf.id,
        filename=sf.original_filename or sf.relative_path or "arquivo.pdf",
        doc_type=sf.doc_type.value,
        size_bytes=sf.size_bytes,
        uploaded_at=sf.uploaded_at,
        status=status,
        transaction_count=sf.transaction_count,
        last_status=sf.last_status.value if sf.last_status else None,
        last_error=sf.last_error,
        pdf_disponivel=bool(sf.stored_path),
        owner_email=owner_email,
    )


@router.get("", response_model=list[FileEntry])
def list_files(
    todos: bool = Query(False, description="Admin: ver arquivos de todos os usuários"),
    user: User = Depends(require_approved_user),
    db: Session = Depends(get_db),
):
    query = db.query(SourceFile)
    if todos and user.role == UserRole.admin:
        query = query.options(joinedload(SourceFile.owner))
        files = query.order_by(SourceFile.uploaded_at.desc()).all()
        return [_to_entry(sf, owner_email=sf.owner.email if sf.owner else None) for sf in files]

    files = query.filter(SourceFile.user_id == user.id).order_by(SourceFile.uploaded_at.desc()).all()
    return [_to_entry(sf) for sf in files]


@router.post("/upload", response_model=FileEntry)
async def upload_file(
    file: UploadFile = File(...),
    user: User = Depends(require_approved_user),
    db: Session = Depends(get_db),
):
    filename = (file.filename or "").lower()
    if not (filename.endswith(".pdf") or filename.endswith(".xlsx")):
        raise HTTPException(status_code=400, detail="Envie um arquivo PDF ou XLSX")

    source_file = save_upload(db, user, file)
    if source_file.size_bytes > MAX_UPLOAD_BYTES:
        db.rollback()
        raise HTTPException(status_code=400, detail="Arquivo maior que 20 MB")
    db.commit()
    db.refresh(source_file)
    return _to_entry(source_file)


def _get_owned_file(db: Session, user: User, file_id) -> SourceFile:
    sf = db.query(SourceFile).filter(SourceFile.id == file_id).one_or_none()
    if sf is None or (sf.user_id != user.id and user.role != UserRole.admin):
        raise HTTPException(status_code=404, detail="Arquivo não encontrado")
    return sf


@router.post("/{file_id}/import", response_model=ImportResult)
def import_file(file_id: str, user: User = Depends(require_approved_user), db: Session = Depends(get_db)):
    sf = _get_owned_file(db, user, file_id)
    try:
        sf = import_source_file(db, sf)
    except FileNotFoundError:
        raise HTTPException(status_code=410, detail="O PDF já foi removido (retenção expirada); não é possível reimportar")
    db.commit()
    return ImportResult(id=sf.id, status=sf.last_status.value, transaction_count=sf.transaction_count, error=sf.last_error)


@router.post("/{file_id}/purge", response_model=FileEntry)
def purge_file(file_id: str, user: User = Depends(require_approved_user), db: Session = Depends(get_db)):
    sf = _get_owned_file(db, user, file_id)
    purge_pdf(sf)
    db.commit()
    db.refresh(sf)
    return _to_entry(sf)
