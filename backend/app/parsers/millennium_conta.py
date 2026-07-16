"""Parser para o extrato de conta à ordem do Millennium BCP, exportado como
XLSX (aba única "Saldos e movimentos", cabeçalho fixo na coluna A-F: Data
lançamento / Data valor / Descrição / Montante / Tipo / Saldo).

As linhas vêm em ordem decrescente de data (mais recente primeiro), com
"Montante" já assinado (negativo = débito) e "Saldo" sendo o saldo corrido
após aquele lançamento — dá pra validar como no extrato do ActivoBank,
conferindo que saldo[i] bate com saldo[i+1] + montante[i].
"""
import re

import openpyxl

from .base import ParseError, RawTransaction

DATE_RE = re.compile(r"^(\d{2})-(\d{2})-(\d{4})$")


def parse_millennium_conta(path: str) -> tuple[list[RawTransaction], int]:
    try:
        wb = openpyxl.load_workbook(path, data_only=True, read_only=True)
    except Exception as e:
        raise ParseError(f"Não foi possível abrir a planilha: {e}")

    ws = wb.worksheets[0]
    rows = list(ws.iter_rows(min_row=1, values_only=True))

    header_idx = None
    for i, row in enumerate(rows):
        if row and row[0] == "Data lançamento" and (row[2] or "").strip() == "Descrição":
            header_idx = i
            break
    if header_idx is None:
        raise ParseError("Cabeçalho 'Data lançamento / Descrição / Montante / Saldo' não encontrado")

    parsed = []
    for row in rows[header_idx + 1 :]:
        data_lanc = row[0] if row else None
        if not isinstance(data_lanc, str) or not DATE_RE.match(data_lanc):
            break  # fim dos dados (linha em branco / rodapé do banco)

        descricao = (row[2] or "").strip()
        montante = row[3]
        saldo = row[5]
        if not descricao or montante is None or saldo is None:
            continue

        montante = float(montante)
        saldo = float(saldo)
        d, m, y = data_lanc.split("-")

        if montante < 0:
            debito, credito = -montante, None
        else:
            debito, credito = None, montante

        parsed.append(
            {
                "date_str": f"{y}/{m}/{d}",
                "descricao": re.sub(r"\s+", " ", descricao),
                "debito": debito,
                "credito": credito,
                "saldo": saldo,
            }
        )

    mismatches = 0
    for i in range(len(parsed) - 1):
        atual, anterior = parsed[i], parsed[i + 1]
        delta = -atual["debito"] if atual["debito"] is not None else atual["credito"]
        esperado = anterior["saldo"] + delta
        if abs(esperado - atual["saldo"]) > 0.005:
            mismatches += 1

    transactions = [
        RawTransaction(date_str=p["date_str"], descricao=p["descricao"], debito=p["debito"], credito=p["credito"])
        for p in parsed
    ]
    return transactions, mismatches
