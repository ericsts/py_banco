# Deploy no droplet

Este app roda em 3 containers (`db`, `backend`, `frontend`) e o **frontend é o
único ponto de entrada** — o nginx dele serve os arquivos estáticos e faz
proxy interno de `/api/*` para o backend (rede Docker interna, `backend:8000`
nunca fica exposto pra fora). Isso significa que seu reverse proxy existente
só precisa apontar **um hostname para a porta do container `frontend`**, sem
se preocupar com o backend.

## 1. Copiar o projeto para o droplet

```
scp -r app/ usuario@seu-droplet:/caminho/dos/seus/projetos/banco-app
```

Ou clonar via git se você colocar isso num repositório.

## 2. Configurar o `.env`

```
cp .env.example .env
```

Edite o `.env` e preencha, no mínimo:

- `SECRET_KEY` — gere com `openssl rand -hex 32`. **Nunca reaproveite** o valor do `.env.example`.
- `ADMIN_EMAIL` / `ADMIN_PASSWORD` — a conta de administrador é criada automaticamente no primeiro start do backend, com esses dados. Troque a senha depois de logar pela primeira vez (não tem tela de troca de senha ainda — se precisar, me avise que eu adiciono).
- `POSTGRES_PASSWORD` — senha forte pro banco.
- `FRONTEND_ORIGIN` — coloque a URL pública que vai apontar pra esse app (ex: `https://banco.seudominio.com`). Usada só como rede de segurança do CORS; como tudo passa pelo proxy do nginx, na prática o navegador nunca faz requisição cross-origin de verdade.
- `RETENTION_DAYS` — quantos dias um PDF enviado fica disponível antes de ser removido do disco (padrão 7). O histórico de lançamentos já importados nunca é apagado por essa rotina.
- `PDF_ROOT_HOST` — só é relevante se você quiser manter a pasta antiga (`../pdf`) montada; pode apontar pra qualquer caminho ou remover a variável se não for usar.

## 3. Subir

```
docker compose up -d --build
```

Isso aplica as migrations do banco automaticamente e cria o usuário admin no
startup do backend.

## 4. Se você já tinha dados de uma instalação anterior (single-user)

Depois do primeiro `up`, rode uma vez:

```
docker compose exec backend python scripts/backfill_admin_owner.py
```

Isso atribui ao admin bootstrap (`ADMIN_EMAIL`) qualquer `source_files`/`transactions`
que já existiam sem dono. Só precisa rodar uma vez.

## 5. Apontar seu reverse proxy

O container `frontend` publica a porta do host definida em `FRONTEND_PORT`
(padrão `5173`) mapeada pra porta `80` interna dele. Aponte seu proxy pra
`http://127.0.0.1:${FRONTEND_PORT}` (ou pro nome do container, se seu proxy
estiver na mesma rede Docker).

### Exemplo com Traefik (labels no docker-compose.yml)

Adicione ao serviço `frontend`, e garanta que ele esteja na mesma rede externa
do seu Traefik:

```yaml
  frontend:
    # ...
    networks:
      - default
      - traefik-public
    labels:
      - traefik.enable=true
      - traefik.http.routers.banco.rule=Host(`banco.seudominio.com`)
      - traefik.http.routers.banco.entrypoints=websecure
      - traefik.http.routers.banco.tls.certresolver=letsencrypt
      - traefik.http.services.banco.loadbalancer.server.port=80

networks:
  traefik-public:
    external: true
```

Nesse caso você pode remover o `ports:` do `frontend` no compose (o Traefik
já expõe pra fora).

### Exemplo com nginx manual + certbot

```nginx
server {
    listen 443 ssl;
    server_name banco.seudominio.com;

    ssl_certificate     /etc/letsencrypt/live/banco.seudominio.com/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/banco.seudominio.com/privkey.pem;

    location / {
        proxy_pass http://127.0.0.1:5173;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
}
```

## 6. Backup

O único dado que precisa de backup é o volume do Postgres (os PDFs enviados
são, por design, temporários — 7 dias — e as transações extraídas já estão no
banco):

```
docker compose exec db pg_dump -U banco banco | gzip > backup-$(date +%F).sql.gz
```

## 7. Adicionando suporte a um banco novo

Quando aparecer um arquivo em quarentena (`/admin/quarentena`) de um banco que
o sistema ainda não reconhece:

1. Veja o texto extraído na própria tela de quarentena.
2. Me peça pra escrever um parser novo (mande o texto ou o PDF).
3. Eu adiciono um `parsers/<banco>.py` + uma entrada em `parsers/registry.py`.
4. Você faz `docker compose up -d --build backend`.
5. Clique em "Reprocessar quarentena" — os arquivos que baterem com o
   template novo são importados automaticamente.
