"""Parser para 'EXTRATO COMBINADO' (extrato de conta) do ActivoBank.

Extrai a seção "CONTA SIMPLES ... EXTRATO DE AAAA/MM/DD A AAAA/MM/DD" e ignora
tudo antes (mensagens, agenda) e depois (empréstimos, seguros) do "SALDO FINAL".

A lógica replica o parser validado manualmente nesta sessão contra os 15
extratos de conta de 2025/2026 (0 divergências de saldo corrido).
"""
import re

from .base import NUM_RE, ParseError, RawTransaction, pdf_to_layout_text, to_float

DATE_LINE_RE = re.compile(r"^\s*(\d{1,2})\.(\d{2})\s+(\d{1,2})\.(\d{2})\s+(.*\S)\s*$")


def parse_conta(pdf_path: str) -> tuple[list[RawTransaction], int]:
    """Retorna (transacoes, mismatches) onde mismatches é a contagem de linhas
    cujo saldo corrido recalculado não bateu com o saldo impresso (serve como
    sinal de baixa confiança na extração, mas não impede a importação)."""
    lines = pdf_to_layout_text(pdf_path)

    start_idx = None
    for i, line in enumerate(lines):
        if "CONTA SIMPLES" in line and "MOEDA: EUR" in line:
            start_idx = i
            break
    if start_idx is None:
        raise ParseError("Seção 'CONTA SIMPLES ... MOEDA: EUR' não encontrada")

    year_start = year_end = None
    for j in range(start_idx, min(start_idx + 6, len(lines))):
        m = re.search(r"EXTRATO DE (\d{4})/(\d{2})/(\d{2}) A (\d{4})/(\d{2})/(\d{2})", lines[j])
        if m:
            year_start = int(m.group(1))
            year_end = int(m.group(4))
            break
    if year_start is None:
        raise ParseError("Linha 'EXTRATO DE ... A ...' não encontrada")

    end_idx = None
    for i in range(start_idx, len(lines)):
        if "SALDO FINAL" in lines[i]:
            end_idx = i
            break
    if end_idx is None:
        raise ParseError("Linha 'SALDO FINAL' não encontrada")

    header_debito = header_credito = None
    saldo_inicial = None
    parsed = []

    for i in range(start_idx, end_idx):
        line = lines[i].rstrip("\n")

        if "DESCRITIVO" in line and "DEBITO" in line and "CREDITO" in line:
            header_debito = line.find("DEBITO")
            header_credito = line.find("CREDITO")
            continue
        if "SALDO INICIAL" in line:
            nums = NUM_RE.findall(line)
            if nums:
                saldo_inicial = to_float(nums[-1])
            continue
        if "A TRANSPORTAR" in line or re.match(r"^\s*TRANSPORTE\s*$", line) or "SALDO DISPONIVEL" in line:
            continue

        m = DATE_LINE_RE.match(line)
        if not m:
            continue
        # Formato no extrato é "MES.DIA" (ex.: "1.02" = 2 de janeiro)
        mes1, dia1, _mes2, _dia2, _rest = m.groups()

        matches = list(NUM_RE.finditer(line))
        if len(matches) < 2:
            continue
        amount_m = matches[-2]
        saldo_m = matches[-1]
        amount_val = to_float(amount_m.group())
        saldo_val = to_float(saldo_m.group())

        date_end = m.end(4)
        descritivo = line[date_end:amount_m.start()].strip()
        descritivo = re.sub(r"\s+", " ", descritivo)
        if not descritivo:
            continue

        if header_debito is None or header_credito is None:
            continue
        mid = (header_debito + header_credito) / 2
        if amount_m.start() < mid:
            debito, credito = amount_val, None
        else:
            debito, credito = None, amount_val

        data_lanc = f"{year_start:04d}/{int(mes1):02d}/{int(dia1):02d}"

        parsed.append(
            {
                "date_str": data_lanc,
                "descricao": descritivo,
                "debito": debito,
                "credito": credito,
                "saldo": saldo_val,
            }
        )

    mismatches = 0
    bal = saldo_inicial
    if bal is not None:
        for t in parsed:
            if t["debito"] is not None:
                bal = bal - t["debito"]
            else:
                bal = bal + t["credito"]
            if abs(bal - t["saldo"]) > 0.005:
                mismatches += 1
            bal = t["saldo"]

    transactions = [
        RawTransaction(date_str=t["date_str"], descricao=t["descricao"], debito=t["debito"], credito=t["credito"])
        for t in parsed
    ]
    return transactions, mismatches
