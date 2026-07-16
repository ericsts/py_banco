"""initial schema

Revision ID: 0001
Revises:
Create Date: 2026-07-14

"""
import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision = "0001"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Cria os tipos ENUM via SQL puro (evita o tipo ser criado duas vezes, um
    # problema conhecido do compilador DDL do SQLAlchemy com ENUM inline em
    # create_table) e referencia com create_type=False nas colunas abaixo.
    op.execute("CREATE TYPE doc_type AS ENUM ('cartao', 'conta', 'unsupported')")
    op.execute("CREATE TYPE import_status AS ENUM ('ok', 'error')")
    op.execute("CREATE TYPE fonte AS ENUM ('cartao', 'conta')")
    op.execute("CREATE TYPE tipo AS ENUM ('debito', 'credito')")

    doc_type = postgresql.ENUM("cartao", "conta", "unsupported", name="doc_type", create_type=False)
    import_status = postgresql.ENUM("ok", "error", name="import_status", create_type=False)
    fonte = postgresql.ENUM("cartao", "conta", name="fonte", create_type=False)
    tipo = postgresql.ENUM("debito", "credito", name="tipo", create_type=False)

    op.create_table(
        "source_files",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("relative_path", sa.String(1024), nullable=False),
        sa.Column("year", sa.Integer, nullable=False),
        sa.Column("doc_type", doc_type, nullable=False),
        sa.Column("size_bytes", sa.BigInteger, nullable=False),
        sa.Column("mtime", sa.DateTime(timezone=True), nullable=False),
        sa.Column("file_hash", sa.String(64), nullable=False),
        sa.Column("imported_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("last_status", import_status, nullable=False),
        sa.Column("last_error", sa.String, nullable=True),
        sa.Column("transaction_count", sa.Integer, nullable=False, server_default="0"),
        sa.UniqueConstraint("relative_path", name="uq_source_files_relative_path"),
    )

    op.create_table(
        "transactions",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "source_file_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("source_files.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("data", sa.Date, nullable=False),
        sa.Column("fonte", fonte, nullable=False),
        sa.Column("tipo", tipo, nullable=False),
        sa.Column("descricao_original", sa.String(1024), nullable=False),
        sa.Column("grupo", sa.String(256), nullable=False),
        sa.Column("valor", sa.Numeric(12, 2), nullable=False),
        sa.Column("ano_mes", sa.String(7), nullable=False),
        sa.Column("excluido", sa.Boolean, nullable=False, server_default=sa.false()),
        sa.Column("excluido_motivo", sa.String(256), nullable=True),
    )
    op.create_index("ix_transactions_source_file_id", "transactions", ["source_file_id"])
    op.create_index("ix_transactions_ano_mes", "transactions", ["ano_mes"])
    op.create_index("ix_transactions_grupo", "transactions", ["grupo"])


def downgrade() -> None:
    op.drop_index("ix_transactions_grupo", table_name="transactions")
    op.drop_index("ix_transactions_ano_mes", table_name="transactions")
    op.drop_index("ix_transactions_source_file_id", table_name="transactions")
    op.drop_table("transactions")
    op.drop_table("source_files")

    op.execute("DROP TYPE tipo")
    op.execute("DROP TYPE fonte")
    op.execute("DROP TYPE import_status")
    op.execute("DROP TYPE doc_type")
