"""multiusuário + upload + quarentena

Revision ID: 0002
Revises: 0001
Create Date: 2026-07-15

"""
import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision = "0002"
down_revision = "0001"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("CREATE TYPE user_role AS ENUM ('admin', 'user')")
    op.execute("CREATE TYPE user_status AS ENUM ('pending', 'approved', 'rejected')")

    user_role = postgresql.ENUM("admin", "user", name="user_role", create_type=False)
    user_status = postgresql.ENUM("pending", "approved", "rejected", name="user_status", create_type=False)

    op.create_table(
        "users",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("email", sa.String(320), nullable=False, unique=True),
        sa.Column("password_hash", sa.String(128), nullable=False),
        sa.Column("role", user_role, nullable=False, server_default="user"),
        sa.Column("status", user_status, nullable=False, server_default="pending"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("approved_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("approved_by_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id"), nullable=True),
    )
    op.create_index("ix_users_email", "users", ["email"])

    # import_status ganha o valor 'pending' (arquivo enviado mas ainda não importado)
    op.execute("ALTER TYPE import_status ADD VALUE IF NOT EXISTS 'pending'")

    # source_files: relaxa colunas do modelo antigo (scan de diretório) e
    # adiciona as do modelo novo (upload multiusuário)
    op.drop_constraint("uq_source_files_relative_path", "source_files", type_="unique")
    op.alter_column("source_files", "relative_path", nullable=True)
    op.alter_column("source_files", "year", nullable=True)
    op.alter_column("source_files", "mtime", nullable=True)
    op.alter_column("source_files", "imported_at", nullable=True, server_default=None)
    # o valor 'pending' do enum é aplicado pelo default do modelo SQLAlchemy
    # (Python-side), não por server_default, pra não usar o valor novo do
    # enum na mesma transação em que ele é criado (restrição do Postgres).

    op.add_column("source_files", sa.Column("user_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id"), nullable=True))
    op.add_column("source_files", sa.Column("original_filename", sa.String(512), nullable=True))
    op.add_column("source_files", sa.Column("stored_path", sa.String(1024), nullable=True))
    op.add_column("source_files", sa.Column("uploaded_at", sa.DateTime(timezone=True), nullable=True))
    op.add_column("source_files", sa.Column("pdf_purged_at", sa.DateTime(timezone=True), nullable=True))
    op.add_column("source_files", sa.Column("template_key", sa.String(64), nullable=True))
    op.create_index("ix_source_files_user_id", "source_files", ["user_id"])

    op.add_column("transactions", sa.Column("user_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id"), nullable=True))
    op.create_index("ix_transactions_user_id", "transactions", ["user_id"])


def downgrade() -> None:
    op.drop_index("ix_transactions_user_id", table_name="transactions")
    op.drop_column("transactions", "user_id")

    op.drop_index("ix_source_files_user_id", table_name="source_files")
    op.drop_column("source_files", "template_key")
    op.drop_column("source_files", "pdf_purged_at")
    op.drop_column("source_files", "uploaded_at")
    op.drop_column("source_files", "stored_path")
    op.drop_column("source_files", "original_filename")
    op.drop_column("source_files", "user_id")

    op.alter_column("source_files", "imported_at", nullable=False, server_default=sa.func.now())
    op.alter_column("source_files", "mtime", nullable=False)
    op.alter_column("source_files", "year", nullable=False)
    op.alter_column("source_files", "relative_path", nullable=False)
    op.create_unique_constraint("uq_source_files_relative_path", "source_files", ["relative_path"])

    op.drop_index("ix_users_email", table_name="users")
    op.drop_table("users")
    op.execute("DROP TYPE user_status")
    op.execute("DROP TYPE user_role")
