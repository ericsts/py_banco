# py_banco.

Gestão de extratos bancários: upload de PDFs de extrato/cartão, extração
automática dos lançamentos e um painel para acompanhar gastos por mês e
categoria. Multiusuário, com aprovação de cadastro pelo admin.

## Como funciona

1. Cada usuário faz upload dos PDFs de extrato ou fatura de cartão.
2. O backend identifica o banco/template do arquivo e extrai os lançamentos
   (data, descrição, grupo/categoria, valor, tipo débito/crédito).
3. Arquivos de um template não reconhecido caem em **quarentena** — o admin
   pode revisar, e quando um parser novo é adicionado, reprocessar em lote.
4. O PDF original fica disponível por um período configurável
   (`RETENTION_DAYS`, padrão 7 dias) e depois é removido do disco — os
   lançamentos já importados continuam no banco indefinidamente.
5. O painel mostra resumo mensal e lista de transações, com filtros.

## Stack

- **Backend**: FastAPI + SQLAlchemy + Alembic, Postgres, autenticação JWT
- **Frontend**: Vue 3 + TypeScript + Tailwind, via Vite
- **Deploy**: Docker Compose (3 containers: `db`, `backend`, `frontend`) —
  o nginx do container `frontend` é o único ponto de entrada e já faz proxy
  interno de `/api/*` para o `backend`

## Rodando localmente

```bash
cp .env.example .env
# edite o .env — pelo menos SECRET_KEY, ADMIN_EMAIL, ADMIN_PASSWORD
docker compose up --build -d
```

Acesse `http://localhost:${FRONTEND_PORT}` (padrão `5173`). O usuário admin
definido em `ADMIN_EMAIL`/`ADMIN_PASSWORD` é criado automaticamente no
primeiro start.

## Deploy em produção

Veja [`deploy.help`](deploy.help) (passo a passo completo para DigitalOcean
Droplet + nginx + Let's Encrypt + GitHub Actions) e [`DEPLOY.md`](DEPLOY.md)
(configuração do `.env`, backup, exemplos alternativos de reverse proxy e
como adicionar suporte a um banco novo).

## Estrutura

```
backend/    FastAPI + SQLAlchemy + Alembic
frontend/   Vue 3 + TypeScript + Tailwind
files/      dados locais (extratos pessoais) — ignorado pelo git
```
