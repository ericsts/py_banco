from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from ..auth import require_approved_user
from ..db import get_db
from ..models import User
from ..schemas import SummaryRow
from ..services.tx_query import compute_summary

router = APIRouter(prefix="/api/summary", tags=["summary"])


@router.get("", response_model=list[SummaryRow])
def summary(
    db: Session = Depends(get_db),
    user: User = Depends(require_approved_user),
    por: str = Query("grupo", pattern="^(grupo|fonte)$"),
    tipo: str = "debito",
    todos: bool = False,
):
    rows = compute_summary(db, user, por=por, tipo=tipo, todos=todos)
    return [SummaryRow(chave=r["chave"], valores=r["valores"], total=r["total"]) for r in rows]
