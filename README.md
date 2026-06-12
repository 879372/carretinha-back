# Playground Móvel — Backend

API Django + WebSocket para gestão de sessões do playground móvel.

## Stack

| Camada | Tecnologia |
|--------|-----------|
| Framework | Django 5 + DRF |
| ASGI / WebSocket | Daphne + Django Channels |
| Banco | PostgreSQL (Railway) |
| Cache / WS broker | Redis (Railway) |
| Auth | JWT (simplejwt) |
| Deploy | Railway |

## Instalação local

```bash
python -m venv venv
source venv/bin/activate      # Windows: venv\Scripts\activate
pip install -r requirements.txt

cp .env.example .env
# edite .env com suas credenciais locais

python manage.py migrate
python manage.py createsuperuser
python manage.py runserver
```

## Endpoints principais

### Auth
| Método | URL | Descrição |
|--------|-----|-----------|
| POST | `/api/auth/login/` | Login → retorna access + refresh token |
| POST | `/api/auth/refresh/` | Renova o access token |

### Sessões (requer JWT)
| Método | URL | Descrição |
|--------|-----|-----------|
| GET | `/api/sessions/` | Lista sessões (filtros: ?status=running&date=2024-06-11) |
| POST | `/api/sessions/` | Cria sessão + criança (inline ou por child_id) |
| POST | `/api/sessions/{id}/start/` | Inicia o timer |
| POST | `/api/sessions/{id}/pause/` | Pausa |
| POST | `/api/sessions/{id}/resume/` | Retoma |
| POST | `/api/sessions/{id}/finish/` | Finaliza manualmente |
| PATCH | `/api/sessions/{id}/confirm_payment/` | Confirma pagamento |
| GET | `/api/sessions/public/{public_token}/` | **Sem auth** — link do responsável |

### Crianças (requer JWT)
| Método | URL | Descrição |
|--------|-----|-----------|
| GET | `/api/sessions/children/` | Lista + busca (?q=nome ou whatsapp) |
| POST | `/api/sessions/children/` | Cadastra manualmente |

### Marketing (requer JWT)
| Método | URL | Descrição |
|--------|-----|-----------|
| GET | `/api/marketing/contacts/` | Lista responsáveis únicos |
| GET | `/api/marketing/contacts/export/` | Exporta CSV |
| GET | `/api/marketing/whatsapp-links/` | Gera links wa.me com mensagem |
| GET | `/api/marketing/stats/` | Receita do dia, totais |

## WebSocket

Conectar em: `ws://<host>/ws/session/<public_token>/`

Mensagens recebidas:
```json
// Tick a cada segundo (enquanto status=running)
{ "type": "tick", "data": { ...SessionDetail } }

// Atualização imediata (start/pause/finish chamados pelo operador)
{ "type": "update", "data": { ...SessionDetail } }
```

Campos úteis em `data`:
- `remaining_seconds` — segundos restantes
- `elapsed_seconds` — segundos decorridos
- `status` — waiting | running | paused | finished | expired
- `child.name` — nome da criança

## Criando uma sessão (exemplo)

```json
POST /api/sessions/
Authorization: Bearer <token>

{
  "child_name": "Ana Clara",
  "child_age": 5,
  "guardian_name": "Maria",
  "guardian_whatsapp": "84991234567",
  "plan": "25",
  "payment_method": "pix",
  "payment_confirmed": true,
  "amount_paid": "20.00"
}
```

Resposta inclui `public_url_path: "/ver/<public_token>"` — envie esse link para o responsável.

## Deploy no Railway

1. Crie projeto no Railway
2. Adicione serviço **PostgreSQL** → copie `DATABASE_URL`
3. Adicione serviço **Redis** → copie `REDIS_URL`
4. Suba o código (GitHub ou Railway CLI)
5. Configure as variáveis de ambiente (veja `.env.example`)
6. O `railway.toml` cuida do resto

## Estrutura de pastas

```
playground-backend/
├── playground/          # Config do projeto (settings, urls, asgi)
├── sessions_app/        # Core: Session, Child, WebSocket consumer
├── marketing/           # Exportação de contatos, stats
├── requirements.txt
├── manage.py
├── Procfile
├── railway.toml
└── .env.example
```
