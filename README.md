# Stride

Stride is a conversational sports-commerce assistant. A React chat UI streams
requests to FastAPI, LangGraph routes each turn into `search`, `compare`,
`recommend`, or `plan`, and Qwen (via Ollama) explains grounded results from
PostgreSQL/pgvector. Cart actions stay in the browser with a mock checkout.

## Architecture

- `frontend/` — React 19, TypeScript, Vite, Tailwind, shadcn/Radix UI, Vitest
- `backend/` — FastAPI, LangGraph, Pydantic, SQLAlchemy, Alembic, Pytest
- PostgreSQL 16 + pgvector — sports catalog, conversation history, checkpoints
- Ollama + `qwen2.5:1.5b` — local structured intent/routing assistance
- `all-MiniLM-L6-v2` — local product and query embeddings

```text
Chat UI  →  Conversation SSE API  →  LangGraph
                                      ├─ search
                                      ├─ compare
                                      ├─ recommend
                                      └─ plan
                                           ↓
                                  PostgreSQL / pgvector
```

External dependencies degrade safely. When Ollama, embeddings, or PostgreSQL
are unavailable, the backend uses deterministic heuristics, seeded products,
and in-memory conversation storage so the UI remains usable.

## Prerequisites

- Node.js 22 or newer
- Python 3.11 or newer
- Docker Desktop
- Ollama

Install the local language model once:

```powershell
ollama pull qwen2.5:1.5b
```

## Run the complete stack

Ollama must be running on Windows before the containers start.

```powershell
Copy-Item .env.example .env
docker compose up --build
```

Open:

- Application: http://localhost:8080
- API documentation: http://localhost:8000/docs
- API health: http://localhost:8000/api/v1/system/health

The first backend image build downloads the MiniLM embedding model and can take
several minutes. Database migrations and product seeding run automatically.
Stop with `docker compose down`; add `-v` only when you intentionally want to
erase the database volume.

## Run services directly while learning

Backend:

```powershell
cd backend
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
Copy-Item .env.example .env
python -c "from sentence_transformers import SentenceTransformer; SentenceTransformer('sentence-transformers/all-MiniLM-L6-v2')"
uvicorn app.main:app --reload --port 8001
```

Use port `8001` when Docker already occupies `8000`.

Frontend, in a second terminal:

```powershell
cd frontend
npm install
Copy-Item .env.example .env
npm run dev
```

Open http://localhost:5173. The chat UI includes a bounded demo fallback when
the backend is unavailable.

## Conversation API

- `POST /api/v1/conversations`
- `GET /api/v1/conversations/{thread_id}` with `X-Conversation-Token`
- `POST /api/v1/conversations/{thread_id}/messages/stream` with
  `X-Conversation-Token`

Stream body:

```json
{
  "content": "Recommend running shoes under 8000",
  "request_id": "00000000-0000-4000-8000-000000000001",
  "intent": "recommend"
}
```

`intent` is optional. When omitted, the graph classifies the turn.
SSE events include `metadata`, `status`, `products`, `comparison`,
`recommendation`, `plan`, `token`, `done`, and `error`. The `done` event
contains the complete assistant envelope.

Legacy product search endpoints remain available:

- `GET /api/v1/system/health`
- `GET /api/v1/products/categories`
- `POST /api/v1/shopping/parse-query`
- `POST /api/v1/shopping/search`
- `POST /api/v1/shopping/smart-search`

## Cart and checkout

The cart is browser-local, persisted in `localStorage`, and uses catalog prices
from product payloads. Checkout is a mock confirmation dialog only. There are
no accounts, payments, inventory reservations, taxes, or shipping integrations
in this version. Model output never mutates the cart; the UI requires an
explicit user action.

## Catalog and future Decathlon data

Development uses a synthetic sports catalog with SKUs, brands, sports, and
comparison specifications. A future ingestion path should accept a permitted
CSV/feed, normalize products, generate embeddings, and upsert into PostgreSQL.
Do not scrape third-party sites unless the terms of use and robots policy
explicitly allow it.

## Quality checks

```powershell
cd frontend
npm test
npm run lint
npm run typecheck
npm run build

cd ..\backend
pytest
```

With the API and database running:

```powershell
cd backend
python -m scripts.evaluate_search
python -m scripts.evaluate_conversations
```

## Security note

- `API_KEY` is an optional lightweight service gate and is visible if compiled
  into browser assets.
- Conversation threads are anonymous and protected by a high-entropy
  `X-Conversation-Token`. Store the token locally per thread.
- Production user accounts should use sessions or OAuth/OIDC with server-side
  authorization.
