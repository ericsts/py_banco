from fastapi import APIRouter, Depends, Query
from sqlalchemy import func
from sqlalchemy.orm import Session

from ..auth import require_approved_user
from ..db import get_db
from ..models import Transaction, User, UserRole
from ..schemas import SummaryRow

router = APIRouter(prefix="/api/summary", tags=["summary"])


@router.get("", response_model=list[SummaryRow])
def summary(
    db: Session = Depends(get_db),
    user: User = Depends(require_approved_user),
    por: str = Query("grupo", pattern="^(grupo|fonte)$"),
    tipo: str = "debito",
    todos: bool = False,
):
    key_col = Transaction.grupo if por == "grupo" else Transaction.fonte

    query = db.query(key_col, Transaction.ano_mes, func.sum(Transaction.valor)).filter(
        Transaction.tipo == tipo, Transaction.excluido.is_(False)
    )
    if not (todos and user.role == UserRole.admin):
        query = query.filter(Transaction.user_id == user.id)
    rows = query.group_by(key_col, Transaction.ano_mes).all()

    by_key: dict[str, dict[str, float]] = {}
    for key, ano_mes, total in rows:
        key = key.value if hasattr(key, "value") else key
        by_key.setdefault(key, {})[ano_mes] = float(total)

    result = []
    for key, valores in by_key.items():
        result.append(SummaryRow(chave=key, valores=valores, total=round(sum(valores.values()), 2)))
    result.sort(key=lambda r: r.total, reverse=True)
    return result
