from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session, joinedload

from ..auth import require_admin
from ..db import get_db
from ..models import DocType, SourceFile, User, UserStatus
from ..parsers.base import pdf_to_layout_text
from ..services.importer import reprocess_quarantine

router = APIRouter(prefix="/api/admin", tags=["admin"])


class UserAdminOut(BaseModel):
    id: str
    email: str
    role: str
    status: str
    created_at: datetime

    class Config:
        from_attributes = True


@router.get("/users", response_model=list[UserAdminOut])
def list_users(status_filtro: str | None = None, admin: User = Depends(require_admin), db: Session = Depends(get_db)):
    query = db.query(User)
    if status_filtro:
        query = query.filter(User.status == status_filtro)
    users = query.order_by(User.created_at.desc()).all()
    return [
        UserAdminOut(id=str(u.id), email=u.email, role=u.role.value, status=u.status.value, created_at=u.created_at)
        for u in users
    ]


@router.post("/users/{user_id}/approve", response_model=UserAdminOut)
def approve_user(user_id: str, admin: User = Depends(require_admin), db: Session = Depends(get_db)):
    target = db.query(User).filter(User.id == user_id).one_or_none()
    if target is None:
        raise HTTPException(status_code=404, detail="Usuário não encontrado")
    target.status = UserStatus.approved
    target.approved_at = datetime.now(timezone.utc)
    target.approved_by_id = admin.id
    db.commit()
    db.refresh(target)
    return UserAdminOut(
        id=str(target.id), email=target.email, role=target.role.value, status=target.status.value, created_at=target.created_at
    )


@router.post("/users/{user_id}/reject", response_model=UserAdminOut)
def reject_user(user_id: str, admin: User = Depends(require_admin), db: Session = Depends(get_db)):
    target = db.query(User).filter(User.id == user_id).one_or_none()
    if target is None:
        raise HTTPException(status_code=404, detail="Usuário não encontrado")
    target.status = UserStatus.rejected
    db.commit()
    db.refresh(target)
    return UserAdminOut(
        id=str(target.id), email=target.email, role=target.role.value, status=target.status.value, created_at=target.created_at
    )


class QuarantineEntryOut(BaseModel):
    id: str
    filename: str
    owner_email: str
    uploaded_at: datetime | None
    size_bytes: int
    pdf_disponivel: bool


@router.get("/quarentena", response_model=list[QuarantineEntryOut])
def list_quarantine(admin: User = Depends(require_admin), db: Session = Depends(get_db)):
    files = (
        db.query(SourceFile)
        .options(joinedload(SourceFile.owner))
        .filter(SourceFile.doc_type == DocType.unsupported)
        .order_by(SourceFile.uploaded_at.desc())
        .all()
    )
    return [
        QuarantineEntryOut(
            id=str(sf.id),
            filename=sf.original_filename or "arquivo.pdf",
            owner_email=sf.owner.email if sf.owner else "?",
            uploaded_at=sf.uploaded_at,
            size_bytes=sf.size_bytes,
            pdf_disponivel=bool(sf.stored_path),
        )
        for sf in files
    ]


@router.get("/quarentena/{file_id}/preview")
def preview_quarantine(file_id: str, admin: User = Depends(require_admin), db: Session = Depends(get_db)):
    sf = db.query(SourceFile).filter(SourceFile.id == file_id).one_or_none()
    if sf is None:
        raise HTTPException(status_code=404, detail="Arquivo não encontrado")
    if not sf.stored_path:
        raise HTTPException(status_code=410, detail="Arquivo já foi removido (retenção)")

    if sf.stored_path.lower().endswith(".xlsx"):
        import openpyxl

        wb = openpyxl.load_workbook(sf.stored_path, data_only=True, read_only=True)
        linhas = []
        for ws in wb.worksheets:
            linhas.append(f"--- aba: {ws.title} ---")
            for row in ws.iter_rows(min_row=1, max_row=60, values_only=True):
                linhas.append("\t".join("" if c is None else str(c) for c in row))
        texto = "\n".join(linhas)
    else:
        lines = pdf_to_layout_text(sf.stored_path)
        texto = "\n".join(lines[:600])

    return {"filename": sf.original_filename, "texto": texto}


@router.post("/quarentena/reprocessar")
def reprocess_all_quarantine(admin: User = Depends(require_admin), db: Session = Depends(get_db)):
    files = db.query(SourceFile).filter(SourceFile.doc_type == DocType.unsupported).all()
    resolved = 0
    for sf in files:
        if reprocess_quarantine(db, sf):
            resolved += 1
    db.commit()
    return {"analisados": len(files), "resolvidos": resolved}
