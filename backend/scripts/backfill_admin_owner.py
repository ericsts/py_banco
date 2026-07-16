"""Atribui ao admin bootstrap (ADMIN_EMAIL) os source_files/transactions que
já existiam antes do upgrade multiusuário (user_id NULL). Rodar uma única vez
depois de aplicar a migration 0002 e subir o backend (que faz o bootstrap do
admin no startup).

Uso: docker compose exec backend python scripts/backfill_admin_owner.py
"""
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.config import settings
from app.db import SessionLocal
from app.models import SourceFile, Transaction, User


def main():
    db = SessionLocal()
    try:
        admin = db.query(User).filter(User.email == settings.admin_email).one_or_none()
        if admin is None:
            print(f"Admin '{settings.admin_email}' não encontrado — suba o backend uma vez antes (ele cria o admin no startup).")
            sys.exit(1)

        n_files = db.query(SourceFile).filter(SourceFile.user_id.is_(None)).update({"user_id": admin.id})
        n_tx = db.query(Transaction).filter(Transaction.user_id.is_(None)).update({"user_id": admin.id})
        db.commit()
        print(f"OK: {n_files} source_files e {n_tx} transactions atribuídos a {admin.email}")
    finally:
        db.close()


if __name__ == "__main__":
    main()
