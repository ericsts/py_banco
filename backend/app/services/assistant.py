import json
import logging
from collections.abc import Generator
from datetime import date
from decimal import Decimal

import anthropic
from sqlalchemy.orm import Session

from ..config import settings
from ..models import ChatMessage, ChatRole, User
from . import tx_query

logger = logging.getLogger(__name__)

MODEL = "claude-opus-4-8"
MAX_TOKENS = 4096
MAX_HISTORY_MESSAGES = 20
MAX_TOOL_ITERATIONS = 6

TOOLS = [
    {
        "name": "list_transactions",
        "description": (
            "Lista lançamentos financeiros do usuário autenticado, com filtros opcionais. "
            "Use quando precisar de detalhes de transações individuais (datas, descrições, "
            "valores exatos) — ex.: 'quais foram minhas compras na Amazon em junho', 'liste "
            "lançamentos acima de 100 euros no mês passado'. Resultados sempre limitados ao "
            "usuário atual, ordenados do mais recente para o mais antigo."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "ano_mes": {
                    "type": "string",
                    "description": "Formato 'YYYY-MM', ex. '2026-06'. Omita para não filtrar por mês.",
                },
                "fonte": {"type": "string", "enum": ["cartao", "conta"]},
                "grupo": {
                    "type": "string",
                    "description": "Nome exato da categoria (use list_categories_and_months para confirmar).",
                },
                "tipo": {"type": "string", "enum": ["debito", "credito"]},
                "q": {"type": "string", "description": "Busca textual livre na descrição original."},
                "limit": {"type": "integer", "minimum": 1, "maximum": 100, "default": 20},
            },
            "required": [],
        },
    },
    {
        "name": "get_spending_summary",
        "description": (
            "Retorna totais agregados por categoria ('grupo') ou fonte ('cartao'/'conta'), "
            "quebrados por mês, para o usuário atual. Prefira esta ferramenta a "
            "list_transactions quando a pergunta for sobre totais/tendências, não sobre "
            "lançamentos individuais — ex.: 'quais minhas maiores categorias de gasto', "
            "'como evoluíram meus gastos com supermercado nos últimos meses'."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "por": {"type": "string", "enum": ["grupo", "fonte"], "default": "grupo"},
                "tipo": {"type": "string", "enum": ["debito", "credito"], "default": "debito"},
            },
            "required": [],
        },
    },
    {
        "name": "list_categories_and_months",
        "description": (
            "Lista os nomes exatos de todas as categorias (grupos) e todos os meses "
            "(YYYY-MM) com lançamentos para o usuário atual. Use antes de filtrar por um "
            "grupo específico, para confirmar o nome exato (ex. 'Pingo Doce (supermercado)')."
        ),
        "input_schema": {"type": "object", "properties": {}, "required": []},
    },
]

TOOL_STATUS_LABELS = {
    "list_transactions": "Consultando transações...",
    "get_spending_summary": "Calculando resumo de gastos...",
    "list_categories_and_months": "Consultando categorias disponíveis...",
}


def _json_default(o):
    if isinstance(o, Decimal):
        return float(o)
    if isinstance(o, date):
        return o.isoformat()
    raise TypeError(f"Objeto não serializável: {o!r}")


def execute_tool(db: Session, user: User, name: str, tool_input: dict) -> str:
    if name == "list_transactions":
        rows = tx_query.list_transactions_for_user(db, user, **tool_input)
        data = [
            {
                "data": t.data,
                "fonte": t.fonte.value,
                "tipo": t.tipo.value,
                "descricao": t.descricao_original,
                "grupo": t.grupo,
                "valor": t.valor,
                "ano_mes": t.ano_mes,
            }
            for t in rows
        ]
    elif name == "get_spending_summary":
        data = tx_query.compute_summary(db, user, **tool_input)
    elif name == "list_categories_and_months":
        data = {
            "grupos": tx_query.list_grupos_for_user(db, user),
            "meses": tx_query.list_meses_for_user(db, user),
        }
    else:
        raise ValueError(f"Ferramenta desconhecida: {name}")
    return json.dumps(data, default=_json_default, ensure_ascii=False)


def _build_system_prompt(db: Session, user: User) -> str:
    meses = tx_query.list_meses_for_user(db, user)
    date_range = f"{meses[-1]} a {meses[0]}" if meses else "nenhum dado disponível ainda"
    top = tx_query.compute_summary(db, user, por="grupo", tipo="debito")[:5]
    top_str = "; ".join(f"{r['chave']}: €{r['total']:.2f}" for r in top) or "sem dados"

    return f"""Você é um consultor financeiro pessoal integrado ao Banco, um app de gestão \
de extratos bancários. Ajude o usuário a entender seus próprios gastos e receitas de forma \
clara e prática.

Hoje é {date.today().isoformat()}. Todos os valores estão em euros (EUR) — formate como \
"€1.234,56".

Contexto rápido (pode estar levemente desatualizado — use as ferramentas para números exatos):
- Dados disponíveis: {date_range}.
- Maiores categorias de despesa: {top_str}.

Você tem três ferramentas para consultar dados sob demanda: list_transactions (lançamentos \
individuais), get_spending_summary (totais por categoria/fonte e mês), \
list_categories_and_months (nomes exatos disponíveis). Use-as sempre que precisar de números \
exatos ou detalhes que não estão no contexto acima. Nunca invente valores.

Responda sempre em português (pt-PT), em tom direto e prestativo. Pode usar Markdown (listas, \
negrito, tabelas simples) quando ajudar a clareza — especialmente em detalhamentos de gastos. \
Seja conciso.

Você só tem acesso aos dados financeiros do próprio usuário autenticado, independentemente do \
papel dele no sistema — nunca assuma acesso a dados de outros usuários."""


def _load_history(db: Session, user: User) -> list[ChatMessage]:
    rows = (
        db.query(ChatMessage)
        .filter(ChatMessage.user_id == user.id)
        .order_by(ChatMessage.created_at.desc())
        .limit(MAX_HISTORY_MESSAGES)
        .all()
    )
    return list(reversed(rows))


def _sse(event: str, data: dict) -> str:
    return f"event: {event}\ndata: {json.dumps(data, ensure_ascii=False)}\n\n"


def chat_stream(db: Session, user: User, user_message: str) -> Generator[str, None, None]:
    if not settings.anthropic_api_key:
        yield _sse("error", {"message": "O assistente não está configurado. Contate o administrador.", "retryable": False})
        return

    history = _load_history(db, user)
    db.add(ChatMessage(user_id=user.id, role=ChatRole.user, content=user_message))
    db.commit()

    api_messages = [{"role": m.role.value, "content": m.content} for m in history]
    api_messages.append({"role": "user", "content": user_message})

    client = anthropic.Anthropic(api_key=settings.anthropic_api_key)
    system_prompt = _build_system_prompt(db, user)
    assistant_text_parts: list[str] = []

    try:
        for _ in range(MAX_TOOL_ITERATIONS):
            current_text = ""
            with client.messages.stream(
                model=MODEL,
                max_tokens=MAX_TOKENS,
                system=system_prompt,
                tools=TOOLS,
                messages=api_messages,
            ) as stream:
                for event in stream:
                    if event.type == "content_block_delta" and event.delta.type == "text_delta":
                        current_text += event.delta.text
                        yield _sse("delta", {"text": event.delta.text})
                response = stream.get_final_message()

            if current_text:
                assistant_text_parts.append(current_text)
            api_messages.append({"role": "assistant", "content": response.content})

            if response.stop_reason != "tool_use":
                break

            tool_results = []
            for block in response.content:
                if block.type != "tool_use":
                    continue
                yield _sse("status", {"message": TOOL_STATUS_LABELS.get(block.name, "Consultando dados...")})
                try:
                    result = execute_tool(db, user, block.name, block.input)
                    tool_results.append({"type": "tool_result", "tool_use_id": block.id, "content": result})
                except Exception:
                    logger.exception("Falha ao executar ferramenta %s", block.name)
                    tool_results.append(
                        {
                            "type": "tool_result",
                            "tool_use_id": block.id,
                            "content": "Erro ao consultar os dados.",
                            "is_error": True,
                        }
                    )
            api_messages.append({"role": "user", "content": tool_results})
        else:
            assistant_text_parts.append(
                "\n\n_(análise interrompida por limite de consultas — tente uma pergunta mais específica)_"
            )

        final_text = "".join(assistant_text_parts).strip()
        if final_text:
            db.add(ChatMessage(user_id=user.id, role=ChatRole.assistant, content=final_text))
            db.commit()
        yield _sse("done", {})

    except anthropic.RateLimitError as e:
        logger.warning("Rate limit da API Anthropic: %s", e)
        yield _sse(
            "error",
            {"message": "O assistente está recebendo muitas solicitações. Tente novamente em instantes.", "retryable": True},
        )
    except anthropic.AuthenticationError as e:
        logger.error("Chave da API Anthropic inválida ou ausente: %s", e)
        yield _sse(
            "error",
            {"message": "Não foi possível conectar ao assistente. Contate o administrador.", "retryable": False},
        )
    except anthropic.APIConnectionError as e:
        logger.error("Falha de conexão com a API Anthropic: %s", e)
        yield _sse(
            "error",
            {"message": "Falha de conexão com o assistente. Verifique sua internet e tente novamente.", "retryable": True},
        )
    except anthropic.APIStatusError as e:
        logger.error("Erro da API Anthropic (status %s): %s", e.status_code, e.response.text)
        retryable = e.status_code >= 500 or e.status_code == 429
        yield _sse(
            "error",
            {"message": "O assistente está temporariamente indisponível. Tente novamente em breve.", "retryable": retryable},
        )
    except Exception:
        logger.exception("Falha inesperada no assistente")
        yield _sse("error", {"message": "Ocorreu um erro inesperado. Tente novamente.", "retryable": True})
