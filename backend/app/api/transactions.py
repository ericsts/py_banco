from fastapi import APIRouter, Depends, Query
from sqlalchemy import func
from sqlalchemy.orm import Session, joinedload

from ..auth import require_approved_user
from ..db import get_db
from ..models import SourceFile, Transaction, User
from ..schemas import TransactionOut, TransactionPage
from ..services.tx_query import apply_filters as _apply_filters

router = APIRouter(prefix="/api/transactions", tags=["transactions"])


@router.get("", response_model=TransactionPage)
def list_transactions(
    db: Session = Depends(get_db),
    user: User = Depends(require_approved_user),
    todos: bool = False,
    ano_mes: str | None = None,
    fonte: str | None = None,
    grupo: str | None = None,
    tipo: str | None = None,
    q: str | None = None,
    incluir_excluidos: bool = False,
    page: int = Query(1, ge=1),
    page_size: int = Query(100, ge=1, le=500),
):
    base = db.query(Transaction).join(SourceFile)
    base = _apply_filters(base, user, todos, ano_mes, fonte, grupo, tipo, q, incluir_excluidos)

    total = base.with_entities(func.count(Transaction.id)).scalar()
    total_valor = base.with_entities(func.coalesce(func.sum(Transaction.valor), 0)).scalar()

    subtotais_rows = (
        base.with_entities(Transaction.ano_mes, func.sum(Transaction.valor))
        .group_by(Transaction.ano_mes)
        .all()
    )
    subtotais_mes = {ano_mes: float(soma) for ano_mes, soma in subtotais_rows}

    items = (
        base.options(joinedload(Transaction.source_file))
        .order_by(Transaction.data.desc())
        .offset((page - 1) * page_size)
        .limit(page_size)
        .all()
    )

    out = [
        TransactionOut(
            id=t.id,
            data=t.data,
            fonte=t.fonte.value,
            tipo=t.tipo.value,
            descricao_original=t.descricao_original,
            grupo=t.grupo,
            valor=float(t.valor),
            ano_mes=t.ano_mes,
            excluido=t.excluido,
            excluido_motivo=t.excluido_motivo,
            source_file_nome=t.source_file.original_filename or t.source_file.relative_path or "",
        )
        for t in items
    ]
    return TransactionPage(
        total=total,
        total_valor=float(total_valor),
        subtotais_mes=subtotais_mes,
        items=out,
    )


@router.get("/grupos", response_model=list[str])
def list_grupos(db: Session = Depends(get_db), user: User = Depends(require_approved_user)):
    rows = (
        db.query(Transaction.grupo)
        .filter(Transaction.excluido.is_(False), Transaction.user_id == user.id)
        .distinct()
        .order_by(Transaction.grupo)
        .all()
    )
    return [r[0] for r in rows]


@router.get("/meses", response_model=list[str])
def list_meses(db: Session = Depends(get_db), user: User = Depends(require_approved_user)):
    rows = (
        db.query(Transaction.ano_mes)
        .filter(Transaction.user_id == user.id)
        .distinct()
        .order_by(Transaction.ano_mes.desc())
        .all()
    )
    return [r[0] for r in rows]
