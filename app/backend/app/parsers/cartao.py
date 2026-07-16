"""Parser para 'EXT AUTONOMO CARTAO' (extrato de cartão de crédito) do ActivoBank.

Extrai apenas a seção "DETALHE DOS MOVIMENTOS" (o razão real de lançamentos do
período). A seção "DETALHE DE TRANSAÇÕES COM PAGAMENTO FRACIONADO", que sempre
vem antes, é ignorada por completo: é só um demonstrativo informativo de como
uma compra parcelada se decompõe em capital/juros/IS mês a mês — os valores
que de fato debitam do cartão naquele período já aparecem em
"DETALHE DOS MOVIMENTOS" (compra integral quando ocorre, e depois só
juros/IS de cada mensalidade nos meses seguintes).

Linhas soltas contendo apenas o código de rede ("VIS"/"MC") são ignoradas
naturalmente: não casam com o regex de linha de transação (que exige duas
datas no início).
"""
import re

from .base import NUM_RE, ParseError, RawTransaction, pdf_to_layout_text, to_float

DATE_LINE_RE = re.compile(r"^\s*(\d{4}/\d{2}/\d{2})\s+(\d{4}/\d{2}/\d{2})\s+(.*\S)\s*$")


def parse_cartao(pdf_path: str) -> tuple[list[RawTransaction], int]:
    """Retorna (transacoes, discrepancia) onde discrepancia é o desvio (em
    valor absoluto) entre a soma dos débitos/créditos extraídos e os totais
    impressos em 'RESUMO DE MOVIMENTOS' do próprio extrato (0 = bateu certo)."""
    lines = pdf_to_layout_text(pdf_path)

    resumo_creditos = resumo_debitos = None
    for i, line in enumerate(lines):
        if "RESUMO DE MOVIMENTOS" in line:
            for j in range(i, min(i + 8, len(lines))):
                if "Créditos" in lines[j] and "Débitos" in lines[j]:
                    for k in range(j + 1, min(j + 4, len(lines))):
                        nums = NUM_RE.findall(lines[k])
                        if len(nums) >= 4:
                            resumo_creditos = to_float(nums[1])
                            resumo_debitos = to_float(nums[2])
                            break
                    break
            break

    start_idx = None
    for i, line in enumerate(lines):
        if "DETALHE DOS MOVIMENTOS" in line:
            start_idx = i
            break
    if start_idx is None:
        raise ParseError("Seção 'DETALHE DOS MOVIMENTOS' não encontrada")

    header_debito = header_credito = None
    parsed = []

    for i in range(start_idx, len(lines)):
        line = lines[i].rstrip("\n")

        if "Descritivo" in line and "Débito" in line and "Crédito" in line:
            header_debito = line.find("Débito")
            header_credito = line.find("Crédito")
            continue

        m = DATE_LINE_RE.match(line)
        if not m:
            continue
        date_str, _data_valor, rest = m.groups()

        matches = list(NUM_RE.finditer(line))
        if not matches or header_debito is None or header_credito is None:
            continue
        amount_m = matches[-1]
        amount_val = to_float(amount_m.group())

        descricao = rest[: amount_m.start() - m.start(3)].strip()
        descricao = re.sub(r"\s+", " ", descricao)
        if not descricao:
            continue

        mid = (header_debito + header_credito) / 2
        if amount_m.start() < mid:
            debito, credito = amount_val, None
        else:
            debito, credito = None, amount_val

        parsed.append(RawTransaction(date_str=date_str, descricao=descricao, debito=debito, credito=credito))

    discrepancia = 0.0
    if resumo_creditos is not None and resumo_debitos is not None:
        soma_creditos = sum(t.credito for t in parsed if t.credito is not None)
        soma_debitos = sum(t.debito for t in parsed if t.debito is not None)
        discrepancia = abs(soma_creditos - resumo_creditos) + abs(soma_debitos - resumo_debitos)

    return parsed, discrepancia
