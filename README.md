# Stride

Stride is a conversational sports-commerce assistant. A React chat UI streams each message to FastAPI. LangGraph routes the turn into search, compare, recommend, or plan. Product answers come from a sports catalog in PostgreSQL, and a local Qwen model only explains results that retrieval already produced. The cart stays in the browser. Checkout is a confirmation dialog, not a payment flow.

Intent and explanations use **Qwen2.5-1.5B** through Ollama, constrained to a Pydantic JSON schema. Regex price and budget rules override the model. Keyword heuristics run when Ollama is unavailable. `training/train_qlora.py` can QLoRA-tune that same checkpoint on the agent's three JSON tasks. The API keeps calling the Ollama tag in `OLLAMA_MODEL` until a merged model is imported there.

## How a turn works

1. **Retrieve.** The query is embedded with Sentence-BERT (`all-MiniLM-L6-v2`, 384 dimensions, L2-normalized). PostgreSQL/pgvector ranks products by cosine distance on an HNSW index, with a small boost when the same terms match name, brand, sport, or description. Category and price are hard filters. If the database or the embedding model is down, ranking falls back to lexical match, rating, price, and a seeded catalog.
2. **Route.** LangGraph classifies the turn as `search`, `compare`, `recommend`, or `plan`. The client may also send an explicit intent. Compare builds a specification matrix for named products. Recommend returns the top-ranked item. Plan fills a kit without exceeding the stated budget.
3. **Explain.** Qwen writes a short explanation from those facts only. It is not allowed to add products, prices, or IDs. If the model fails, the API returns the deterministic summary instead.
4. **Stream.** The API sends Server-Sent Events: `metadata`, `status`, `products`, `comparison`, `recommendation`, `plan`, `token`, `done`, and `error`. Repeating the same `request_id` replays the saved answer.

Conversation threads are anonymous. Each thread is gated by an `X-Conversation-Token` stored as a SHA-256 hash and checked with `hmac.compare_digest`. LangGraph checkpoints live in PostgreSQL, with an in-memory saver if that checkpointer cannot start.

```text
Chat UI  →  FastAPI SSE  →  hybrid retrieval (pgvector + keywords)
                         →  LangGraph
                              ├─ search
                              ├─ compare
                              ├─ recommend
                              └─ plan
                                   ↓
                              Qwen2.5 explains the result
```

## Stack

| Layer | Choice |
| --- | --- |
| Frontend | React 19, TypeScript, Vite, Tailwind, shadcn/Radix |
| API | FastAPI, Pydantic, SQLAlchemy, Alembic, Uvicorn |
| Agent | LangGraph state graph, Postgres checkpointer |
| Data | PostgreSQL 16, pgvector, HNSW cosine index |
| Models | Ollama `qwen2.5:1.5b`, optional QLoRA adapter, Sentence-BERT `all-MiniLM-L6-v2` |
| Run | Docker Compose, health checks, Vitest, Pytest |

## Prerequisites

- Docker Desktop
- Ollama, for local model answers
- Node.js 22 or newer and Python 3.11 or newer, only if you run the services outside Docker

Pull the model once:

```bash
ollama pull qwen2.5:1.5b
```

Ollama must be running before the containers start. The backend reaches it at `host.docker.internal:11434`.

## Run with Docker

```bash
cp .env.example .env
docker compose up --build
```

- App: http://localhost:8080
- API docs: http://localhost:8000/docs
- Health: http://localhost:8000/api/v1/system/health

The first backend build downloads the MiniLM model and can take several minutes. Migrations and catalog seeding run on startup. Stop with `docker compose down`. Add `-v` only when you mean to delete the database volume.

## Run the services directly

Backend:

```bash
cd backend
python -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.txt
cp .env.example .env
python -c "from sentence_transformers import SentenceTransformer; SentenceTransformer('sentence-transformers/all-MiniLM-L6-v2')"
uvicorn app.main:app --reload --port 8001
```

Use port `8001` when Docker already occupies `8000`. Point `DATABASE_URL` in `backend/.env` at a running Postgres if you want persistent search. On Windows PowerShell, activate the venv with `.\.venv\Scripts\Activate.ps1`.

Frontend, in a second terminal:

```bash
cd frontend
npm install
cp .env.example .env
npm run dev
```

Open http://localhost:5173. The chat UI has a bounded demo fallback when the backend is down.

## API

- `POST /api/v1/conversations`
- `GET /api/v1/conversations/{thread_id}` with `X-Conversation-Token`
- `POST /api/v1/conversations/{thread_id}/messages/stream` with `X-Conversation-Token`

```json
{
  "content": "Recommend running shoes under 8000",
  "request_id": "00000000-0000-4000-8000-000000000001",
  "intent": "recommend"
}
```

`intent` is optional. When it is omitted, the graph classifies the turn.

Catalog endpoints:

- `GET /api/v1/system/health`
- `GET /api/v1/products/categories`
- `POST /api/v1/shopping/parse-query`
- `POST /api/v1/shopping/search`
- `POST /api/v1/shopping/smart-search`

## Cart

The cart is stored in `localStorage` and priced from catalog payloads. Checkout only confirms the order. There are no accounts, payments, inventory reservations, taxes, or shipping. Model output never changes the cart. Adding an item takes an explicit click.

The development catalog is synthetic: SKUs, brands, sports, and comparison specs. A later import should take an allowed CSV or feed, normalize products, embed them, and upsert into PostgreSQL.

## QLoRA fine-tune

The LangGraph agent asks Qwen for three JSON objects: an intent (`search`, `compare`, `recommend`, `plan`), shopping slots, and a grounded explanation. `training/train_qlora.py` fine-tunes `Qwen/Qwen2.5-1.5B-Instruct` on those exact prompts with 4-bit NF4 QLoRA (rank 8, alpha 16, learning rate `5e-5`, one epoch). Loss is applied only to the assistant JSON.

QLoRA needs an NVIDIA GPU. It will exit on a Mac.

```bash
python -m training.build_dataset
pip install -r training/requirements.txt
python -m training.train_qlora
```

The adapter is written to `training/outputs/stride_qwen25_1_5b_qlora`. Ollama cannot load that adapter file. Merge it into the base model, convert the result to GGUF, then `ollama create` a model and set `OLLAMA_MODEL` to that name. Until then the API keeps using `qwen2.5:1.5b`.

## Checks

```bash
cd frontend
npm test
npm run lint
npm run typecheck
npm run build

cd ../backend
pytest
```

With the API and database running:

```bash
cd backend
python -m scripts.evaluate_search
python -m scripts.evaluate_conversations
```

`evaluate_search` fails if hybrid retrieval ranks the labeled cases worse than keyword search.

## Deploy

Vercel serves the frontend. A Docker host serves the API and Postgres.

On Vercel, set the root directory to `frontend` and set:

- `VITE_API_BASE_URL` to the public API origin, with no trailing slash
- `VITE_API_KEY` only when the API has `API_KEY` set

If the Vercel project stays on the repository root, `vercel.json` still builds `frontend/`.

On the Docker host, set `POSTGRES_PASSWORD` and `CORS_ORIGINS` in `.env`. `CORS_ORIGINS` is the Vercel origin, for example `https://stride.vercel.app`. Then:

```bash
docker compose -f compose.prod.yaml up --build -d
```

That stack uses the bundled Postgres 16 + pgvector database and turns Ollama and embeddings off, so production answers use the deterministic fallbacks. The API listens on port 8000. Use that public origin as `VITE_API_BASE_URL`, then redeploy the frontend so the value is baked into the build.

## Security

`API_KEY` is an optional service gate. It is visible to anyone if it is compiled into the frontend. Conversation tokens are high-entropy secrets for anonymous threads; keep each token in the browser for that thread. Accounts, if added later, should use server-side sessions or OAuth/OIDC.
