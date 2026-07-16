"""Agrupamento de lançamentos por semelhança de comerciante/entidade.

Port direto das regras validadas em build_planilha.py nesta sessão (mesma
lógica usada para gerar a planilha 'Gastos 2025-2026.xlsx').
"""
import re

LOAN_RE = re.compile(r"(?:EMP\.?\s*N\.?|INCUMPRIMENTO(?:\s+EMP)?)\s*(\d{6,})", re.IGNORECASE)

GROUP_RULES = [
    (r"EST SERVICO|TAXAS POSTOS COMBUSTIVEL", "Combustível (Postos)"),
    (r"\bLIDL\b", "Lidl (supermercado)"),
    (r"PINGO DOCE", "Pingo Doce (supermercado)"),
    (r"CONTINENTE", "Continente (supermercado)"),
    (r"MERCADONA", "Mercadona (supermercado)"),
    (r"\bALDI\b", "Aldi (supermercado)"),
    (r"\bAUCHAN\b", "Auchan (supermercado)"),
    (r"RECHEIO", "Recheio (cash & carry)"),
    (r"NORMALAS|MEUSUPER|MINIMERCADO|HIPER CHINA|MERCEARIA", "Mercearias locais"),
    (r"FARMACIA", "Farmácia"),
    (r"BARBEARIA LORD", "Barbearia Lord"),
    (r"CASA DO CABELO", "Cabeleireiro"),
    (r"COOKIDOO", "Cookidoo (Bimby)"),
    (r"CLAUDE\.AI|ANTHROPIC", "Anthropic Claude (assinatura)"),
    (r"LARAVEL CL", "Laravel Cloud (assinatura)"),
    (r"GOOGLE YOUTUBE|YOUTUBE", "YouTube Premium (assinatura)"),
    (r"FACEBK|FACEBOOK", "Facebook Ads"),
    (r"KLARNA", "Klarna (compras parceladas)"),
    (r"SCALAPAY", "Scalapay (compras parceladas)"),
    (r"BOLT\.EU", "Bolt (transporte)"),
    (r"\bGLOVO\b", "Glovo (entregas)"),
    (r"\bUBER\b", "Uber"),
    (r"TML TRANSP", "Transportes Lisboa (TML)"),
    (r"VIAVERDE", "Portagens (Via Verde)"),
    (r"LEV ATM", "Levantamento Multibanco (ATM)"),
    (r"SERVICOS MUNICIPALIZAD", "Água (Serviços Municipalizados)"),
    (r"ENDESA", "Endesa Energia (eletricidade)"),
    (r"IBERDROLA", "Iberdrola (eletricidade)"),
    (r"\bLOGO\b", "Logo Energia"),
    (r"NOS Comunicacoe", "NOS (telecom)"),
    (r"\bMEO\b", "MEO (telecom)"),
    (r"DIGI PORTUGAL", "Digi (telecom)"),
    (r"ONEY BANK", "Oney Bank (crédito)"),
    (r"SANT CONSUMER|SANTANDER CONSUMER", "Santander Consumer Finance (crédito)"),
    (r"WIZINK", "Wizink Bank (crédito)"),
    (r"CREDIBO", "Banco Credibom (crédito)"),
    (r"BNP PARIBAS PERSONAL", "BNP Paribas Personal Finance (crédito)"),
    (r"LUSITANIA", "Lusitania Seguros"),
    (r"GENERALI", "Generali Seguros"),
    (r"\bIGCP\b|PAG-ESTADO|PAG\.DUC|AUTORIDADE NACIONAL|CAMARA MUNICIPAL|INSTITUTO GESTAO FINAN", "Pagamentos ao Estado (Impostos/Taxas)"),
    (r"IMPOSTO DO SELO|IMP\.?\s*DO SELO|IMP\.?\s*SELO", "Imposto do Selo"),
    (r"JUROS PAG FRACIONADO|DEBITO JUROS", "Juros (cartão/crédito)"),
    (r"COMISSAO TRANSF CREDITO|COMISSAO LEVANTAMENTO|TAXA LIMITE EXCEDIDO|LIMITE EXCEDIDO NO CARTAO|CUSTO DE SERVICO INTERNACIONAL", "Taxas e Comissões (Cartão)"),
    (r"TRANSFERENCIA CARTAO CREDITO", "Transferência Cartão → Conta"),
    (r"\bZARA\b", "Zara"),
    (r"BERSHKA", "Bershka"),
    (r"PULL E BEAR", "Pull & Bear"),
    (r"TEZENIS", "Tezenis"),
    (r"LEFTIES", "Lefties"),
    (r"\bSHEIN\b", "Shein"),
    (r"\bTEMU\b", "Temu"),
    (r"\bIKEA\b", "Ikea"),
    (r"LEROY MERLIN", "Leroy Merlin"),
    (r"SPORT ZONE", "Sport Zone"),
    (r"DECATHLON", "Decathlon"),
    (r"WORTEN", "Worten"),
    (r"STAPLES", "Staples"),
    (r"MCDONALDS|\bMCD\b", "McDonald's"),
    (r"100MONTADITOS", "100 Montaditos"),
]
_COMPILED_RULES = [(re.compile(p, re.IGNORECASE), label) for p, label in GROUP_RULES]

# Transferências para o próprio cartão / pagamentos do cartão feitos pela conta
# já estão refletidos, item a item, no extrato do cartão -> não contam como
# despesa (evita duplicar o gasto).
PAGAMENTO_CARTAO_RE = re.compile(r"PAGAMENTO CARTAO", re.IGNORECASE)


def clean_base(desc: str) -> str:
    s = desc
    s = re.sub(r"^COMPRA\s+\d{3,4}\s+", "", s, flags=re.IGNORECASE)
    s = re.sub(r"\bFracionada\s*x\d+\s*VIS\b", "", s, flags=re.IGNORECASE)
    s = re.sub(r"\bCONTACTLESS\b", "", s, flags=re.IGNORECASE)
    s = re.sub(r"\bCONT\b\s*$", "", s, flags=re.IGNORECASE)
    s = re.sub(r"\s+", " ", s).strip()
    return s if s else desc


def group_desc(desc: str) -> str:
    m = LOAN_RE.search(desc)
    if m:
        return f"Empréstimo Pessoal Nº {m.group(1)}"
    for rx, label in _COMPILED_RULES:
        if rx.search(desc):
            return label
    return clean_base(desc)


def is_pagamento_cartao(desc: str) -> bool:
    return bool(PAGAMENTO_CARTAO_RE.search(desc))
