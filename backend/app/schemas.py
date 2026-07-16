import uuid
from datetime import date, datetime

from pydantic import BaseModel


class FileEntry(BaseModel):
    id: uuid.UUID
    filename: str
    doc_type: str
    size_bytes: int
    uploaded_at: datetime | None
    status: str  # not_imported | imported | error | unsupported
    transaction_count: int | None = None
    last_status: str | None = None
    last_error: str | None = None
    pdf_disponivel: bool
    owner_email: str | None = None


class ImportResult(BaseModel):
    id: uuid.UUID
    status: str
    transaction_count: int
    error: str | None = None


class TransactionOut(BaseModel):
    id: uuid.UUID
    data: date
    fonte: str
    tipo: str
    descricao_original: str
    grupo: str
    valor: float
    ano_mes: str
    excluido: bool
    excluido_motivo: str | None
    source_file_nome: str

    class Config:
        from_attributes = True


class TransactionPage(BaseModel):
    total: int
    total_valor: float
    subtotais_mes: dict[str, float]
    items: list[TransactionOut]


class SummaryRow(BaseModel):
    chave: str
    valores: dict[str, float]
    total: float
