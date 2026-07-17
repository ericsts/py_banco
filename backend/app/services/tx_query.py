from sqlalchemy import func
from sqlalchemy.orm import Session

from ..models import SourceFile, Transaction, User, UserRole


def apply_filters(
    query,
    user: User,
    todos: bool,
    ano_mes: str | None = None,
    fonte: str | None = None,
    grupo: str | None = None,
    tipo: str | None = None,
    q: str | None = None,
    incluir_excluidos: bool = False,
):
    if not (todos and user.role == UserRole.admin):
        query = query.filter(Transaction.user_id == user.id)
    if ano_mes:
        query = query.filter(Transaction.ano_mes == ano_mes)
    if fonte:
        query = query.filter(Transaction.fonte == fonte)
    if grupo:
        query = query.filter(Transaction.grupo == grupo)
    if tipo:
        query = query.filter(Transaction.tipo == tipo)
    if q:
        query = query.filter(Transaction.descricao_original.ilike(f"%{q}%"))
    if not incluir_excluidos:
        query = query.filter(Transaction.excluido.is_(False))
    return query


def list_transactions_for_user(
    db: Session,
    user: User,
    *,
    ano_mes: str | None = None,
    fonte: str | None = None,
    grupo: str | None = None,
    tipo: str | None = None,
    q: str | None = None,
    limit: int = 20,
) -> list[Transaction]:
    """Sempre restrito ao próprio usuário — é o ponto de entrada usado pela
    camada de IA (nunca expõe `todos`)."""
    query = db.query(Transaction).join(SourceFile)
    query = apply_filters(query, user, todos=False, ano_mes=ano_mes, fonte=fonte, grupo=grupo, tipo=tipo, q=q)
    return query.order_by(Transaction.data.desc()).limit(limit).all()


def compute_summary(
    db: Session,
    user: User,
    *,
    por: str = "grupo",
    tipo: str = "debito",
    todos: bool = False,
) -> list[dict]:
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

    result = [
        {"chave": key, "valores": valores, "total": round(sum(valores.values()), 2)}
        for key, valores in by_key.items()
    ]
    result.sort(key=lambda r: r["total"], reverse=True)
    return result


def list_grupos_for_user(db: Session, user: User) -> list[str]:
    rows = (
        db.query(Transaction.grupo)
        .filter(Transaction.excluido.is_(False), Transaction.user_id == user.id)
        .distinct()
        .order_by(Transaction.grupo)
        .all()
    )
    return [r[0] for r in rows]


def list_meses_for_user(db: Session, user: User) -> list[str]:
    rows = (
        db.query(Transaction.ano_mes)
        .filter(Transaction.user_id == user.id)
        .distinct()
        .order_by(Transaction.ano_mes.desc())
        .all()
    )
    return [r[0] for r in rows]
