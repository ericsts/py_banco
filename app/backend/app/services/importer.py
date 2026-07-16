import hashlib
import os
import uuid
from datetime import datetime, timezone

from fastapi import UploadFile
from sqlalchemy.orm import Session

from ..config import settings
from ..models import DocType, Fonte, ImportStatus, SourceFile, Tipo, Transaction, User
from ..parsers.base import ParseError
from ..parsers.registry import REGISTRY, detect_template
from .categorize import group_desc, is_pagamento_cartao


def _file_hash(path: str) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(65536), b""):
            h.update(chunk)
    return h.hexdigest()


def save_upload(db: Session, user: User, upload: UploadFile) -> SourceFile:
    """Salva o arquivo enviado (PDF ou XLSX) em disco (por usuário) e cria o
    registro em source_files já com o tipo detectado pelo conteúdo. Não
    importa os lançamentos ainda — isso acontece quando o usuário clica em
    Importar."""
    user_dir = os.path.join(settings.upload_root, str(user.id))
    os.makedirs(user_dir, exist_ok=True)
    ext = os.path.splitext(upload.filename or "")[1].lower()
    if ext not in (".pdf", ".xlsx"):
        ext = ".pdf"
    stored_path = os.path.join(user_dir, f"{uuid.uuid4()}{ext}")

    with open(stored_path, "wb") as f:
        while chunk := upload.file.read(1024 * 1024):
            f.write(chunk)

    size_bytes = os.path.getsize(stored_path)
    digest = _file_hash(stored_path)
    template = detect_template(stored_path)

    source_file = SourceFile(
        user_id=user.id,
        original_filename=upload.filename or "extrato.pdf",
        stored_path=stored_path,
        uploaded_at=datetime.now(timezone.utc),
        doc_type=template.doc_type if template else DocType.unsupported,
        template_key=template.key if template else None,
        size_bytes=size_bytes,
        file_hash=digest,
        last_status=ImportStatus.pending,
        transaction_count=0,
    )
    db.add(source_file)
    db.flush()
    return source_file


def import_source_file(db: Session, source_file: SourceFile) -> SourceFile:
    """Importa (ou reimporta) os lançamentos de um SourceFile já salvo em
    disco (`stored_path`). Substitui lançamentos de uma importação anterior."""
    if not source_file.stored_path or not os.path.isfile(source_file.stored_path):
        raise FileNotFoundError(source_file.stored_path or "(arquivo já purgado)")

    source_file.imported_at = datetime.now(timezone.utc)
    template = next((t for t in REGISTRY if t.key == source_file.template_key), None)
    if template is None:
        source_file.last_status = ImportStatus.error
        source_file.last_error = "Formato não reconhecido — em quarentena para um template novo ser criado"
        source_file.transaction_count = 0
        db.flush()
        return source_file

    db.query(Transaction).filter(Transaction.source_file_id == source_file.id).delete()

    fonte = Fonte.cartao if template.doc_type == DocType.cartao else Fonte.conta
    try:
        raw_txs, confidence = template.parse(source_file.stored_path)

        rows = []
        for t in raw_txs:
            valor = t.debito if t.debito is not None else t.credito
            tipo = Tipo.debito if t.debito is not None else Tipo.credito
            # "Pagamento do cartão" aparece duas vezes pela natureza da operação:
            # como débito na conta (dinheiro saindo para pagar a fatura) e como
            # crédito no próprio cartão (abatimento da dívida). Nenhum dos dois
            # lados é despesa real nem entrada real — é a mesma transferência
            # interna entre a conta e o cartão vista de dois ângulos.
            e_pagamento_cartao = is_pagamento_cartao(t.descricao)
            excluido = e_pagamento_cartao and (
                (fonte == Fonte.conta and tipo == Tipo.debito) or (fonte == Fonte.cartao and tipo == Tipo.credito)
            )
            rows.append(
                Transaction(
                    user_id=source_file.user_id,
                    source_file=source_file,
                    data=datetime.strptime(t.date_str, "%Y/%m/%d").date(),
                    fonte=fonte,
                    tipo=tipo,
                    descricao_original=t.descricao,
                    grupo=group_desc(t.descricao),
                    valor=valor,
                    ano_mes=t.date_str[:7].replace("/", "-"),
                    excluido=excluido,
                    excluido_motivo="Pagamento do cartão: transferência interna entre conta e cartão, não é despesa nem entrada real" if excluido else None,
                )
            )
        db.add_all(rows)
        source_file.last_status = ImportStatus.ok
        source_file.last_error = None
        source_file.transaction_count = len(rows)
        if confidence and confidence > 0.01:
            source_file.last_error = f"Aviso: divergência de {confidence:.2f} contra os totais impressos no extrato"
    except ParseError as e:
        source_file.last_status = ImportStatus.error
        source_file.last_error = str(e)
        source_file.transaction_count = 0

    db.flush()
    return source_file


def reprocess_quarantine(db: Session, source_file: SourceFile) -> bool:
    """Tenta detectar o template de novo (usado depois que um parser novo é
    registrado). Retorna True se passou a reconhecer e importar com sucesso."""
    if source_file.doc_type != DocType.unsupported:
        return False
    if not source_file.stored_path or not os.path.isfile(source_file.stored_path):
        return False
    template = detect_template(source_file.stored_path)
    if template is None:
        return False
    source_file.doc_type = template.doc_type
    source_file.template_key = template.key
    import_source_file(db, source_file)
    return source_file.last_status == ImportStatus.ok


def purge_pdf(source_file: SourceFile) -> None:
    """Apaga o PDF em disco (mantém o registro e os lançamentos já importados)."""
    if source_file.stored_path and os.path.isfile(source_file.stored_path):
        os.remove(source_file.stored_path)
    source_file.stored_path = None
    source_file.pdf_purged_at = datetime.now(timezone.utc)
