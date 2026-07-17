import enum
import uuid

from sqlalchemy import (
    String,
    Integer,
    BigInteger,
    Boolean,
    Date,
    DateTime,
    Numeric,
    ForeignKey,
    Enum,
    Text,
    func,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .db import Base


class DocType(str, enum.Enum):
    cartao = "cartao"
    conta = "conta"
    unsupported = "unsupported"  # também usado como "não reconhecido / em quarentena"


class ImportStatus(str, enum.Enum):
    pending = "pending"  # ainda não foi importado
    ok = "ok"
    error = "error"


class Fonte(str, enum.Enum):
    cartao = "cartao"
    conta = "conta"


class Tipo(str, enum.Enum):
    debito = "debito"
    credito = "credito"


class UserRole(str, enum.Enum):
    admin = "admin"
    user = "user"


class UserStatus(str, enum.Enum):
    pending = "pending"
    approved = "approved"
    rejected = "rejected"


class ChatRole(str, enum.Enum):
    user = "user"
    assistant = "assistant"


class User(Base):
    __tablename__ = "users"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    email: Mapped[str] = mapped_column(String(320), nullable=False, unique=True, index=True)
    password_hash: Mapped[str] = mapped_column(String(128), nullable=False)
    role: Mapped[UserRole] = mapped_column(Enum(UserRole, name="user_role"), nullable=False, default=UserRole.user)
    status: Mapped[UserStatus] = mapped_column(
        Enum(UserStatus, name="user_status"), nullable=False, default=UserStatus.pending
    )
    created_at: Mapped["DateTime"] = mapped_column(DateTime(timezone=True), server_default=func.now())
    approved_at: Mapped["DateTime | None"] = mapped_column(DateTime(timezone=True), nullable=True)
    approved_by_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id"), nullable=True
    )


class SourceFile(Base):
    __tablename__ = "source_files"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=True)

    # legado do modelo antigo (scan de diretório) — mantidos por compatibilidade com dados já importados
    relative_path: Mapped[str | None] = mapped_column(String(1024), nullable=True)
    year: Mapped[int | None] = mapped_column(Integer, nullable=True)
    mtime: Mapped["DateTime | None"] = mapped_column(DateTime(timezone=True), nullable=True)

    # modelo novo (upload)
    original_filename: Mapped[str | None] = mapped_column(String(512), nullable=True)
    stored_path: Mapped[str | None] = mapped_column(String(1024), nullable=True)
    uploaded_at: Mapped["DateTime | None"] = mapped_column(DateTime(timezone=True), nullable=True)
    pdf_purged_at: Mapped["DateTime | None"] = mapped_column(DateTime(timezone=True), nullable=True)

    doc_type: Mapped[DocType] = mapped_column(Enum(DocType, name="doc_type"), nullable=False)
    template_key: Mapped[str | None] = mapped_column(String(64), nullable=True)
    size_bytes: Mapped[int] = mapped_column(BigInteger, nullable=False)
    file_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    imported_at: Mapped["DateTime | None"] = mapped_column(DateTime(timezone=True), nullable=True)
    last_status: Mapped[ImportStatus] = mapped_column(
        Enum(ImportStatus, name="import_status"), nullable=False, default=ImportStatus.pending
    )
    last_error: Mapped[str | None] = mapped_column(String, nullable=True)
    transaction_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)

    owner: Mapped["User | None"] = relationship(foreign_keys=[user_id])
    transactions: Mapped[list["Transaction"]] = relationship(
        back_populates="source_file", cascade="all, delete-orphan"
    )


class Transaction(Base):
    __tablename__ = "transactions"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=True)
    source_file_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("source_files.id", ondelete="CASCADE"), nullable=False
    )
    data: Mapped["Date"] = mapped_column(Date, nullable=False)
    fonte: Mapped[Fonte] = mapped_column(Enum(Fonte, name="fonte"), nullable=False)
    tipo: Mapped[Tipo] = mapped_column(Enum(Tipo, name="tipo"), nullable=False)
    descricao_original: Mapped[str] = mapped_column(String(1024), nullable=False)
    grupo: Mapped[str] = mapped_column(String(256), nullable=False)
    valor: Mapped[float] = mapped_column(Numeric(12, 2), nullable=False)
    ano_mes: Mapped[str] = mapped_column(String(7), nullable=False)
    excluido: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    excluido_motivo: Mapped[str | None] = mapped_column(String(256), nullable=True)

    source_file: Mapped[SourceFile] = relationship(back_populates="transactions")


class ChatMessage(Base):
    __tablename__ = "chat_messages"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    role: Mapped[ChatRole] = mapped_column(Enum(ChatRole, name="chat_role"), nullable=False)
    content: Mapped[str] = mapped_column(Text, nullable=False)
    created_at: Mapped["DateTime"] = mapped_column(DateTime(timezone=True), server_default=func.now())
