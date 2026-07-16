"""Registro de templates de banco reconhecidos pelo conteúdo do arquivo (PDF
ou XLSX).

Cada usuário pode subir extratos de bancos diferentes, com nomes de arquivo
quaisquer — então a detecção de tipo não pode depender do nome do arquivo
(como fazia o modelo antigo, de pasta local). Em vez disso, cada template
define uma função `sniff(path)` que abre o arquivo do jeito que fizer sentido
pro formato dele (texto via `pdftotext -layout` para PDF, células via
openpyxl para XLSX) e procura strings-assinatura. O primeiro template cujo
sniff bater é usado; se nenhum bater, o arquivo cai em quarentena
(`doc_type=unsupported`) para um parser novo ser escrito depois.

Para adicionar suporte a um banco novo: escrever um parser em
`parsers/<banco>.py` (retorna `(list[RawTransaction], discrepancia_ou_mismatches)`),
escrever a função de sniff (recebe o caminho do arquivo, devolve bool — deve
tolerar receber um arquivo de outro formato sem estourar exceção) e adicionar
um `BankTemplate` na lista `REGISTRY` abaixo.
"""
import logging
from dataclasses import dataclass
from typing import Callable

from ..models import DocType
from .base import RawTransaction, pdf_to_layout_text
from .cartao import parse_cartao
from .conta import parse_conta
from .millennium_conta import parse_millennium_conta

logger = logging.getLogger("registry")


@dataclass
class BankTemplate:
    key: str
    label: str
    doc_type: DocType
    sniff: Callable[[str], bool]
    parse: Callable[[str], tuple[list[RawTransaction], float]]


def _sniff_activobank_cartao(path: str) -> bool:
    text = "\n".join(pdf_to_layout_text(path))
    return "ActivoBank" in text and "DETALHE DOS MOVIMENTOS" in text


def _sniff_activobank_conta(path: str) -> bool:
    text = "\n".join(pdf_to_layout_text(path))
    return "ActivoBank" in text and "CONTA SIMPLES" in text and "EXTRATO DE" in text


def _sniff_millennium_conta(path: str) -> bool:
    import openpyxl

    wb = openpyxl.load_workbook(path, data_only=True, read_only=True)
    ws = wb.worksheets[0]
    text = "\n".join(
        str(cell) for row in ws.iter_rows(min_row=1, max_row=13, values_only=True) for cell in row if cell
    )
    return "millenniumbcp.pt" in text and "Millennium BCP" in text and "Data lançamento" in text


REGISTRY: list[BankTemplate] = [
    BankTemplate(
        key="activobank_cartao",
        label="ActivoBank – Cartão de Crédito",
        doc_type=DocType.cartao,
        sniff=_sniff_activobank_cartao,
        parse=parse_cartao,
    ),
    BankTemplate(
        key="activobank_conta",
        label="ActivoBank – Conta à Ordem",
        doc_type=DocType.conta,
        sniff=_sniff_activobank_conta,
        parse=parse_conta,
    ),
    BankTemplate(
        key="millennium_conta",
        label="Millennium BCP – Conta à Ordem",
        doc_type=DocType.conta,
        sniff=_sniff_millennium_conta,
        parse=parse_millennium_conta,
    ),
]


def detect_template(path: str) -> BankTemplate | None:
    for tpl in REGISTRY:
        try:
            if tpl.sniff(path):
                return tpl
        except Exception:
            logger.debug("sniff de %s falhou para %s (formato diferente, esperado)", tpl.key, path)
    return None
