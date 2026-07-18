# Stride — Tech Stack

Complete technology stack for **Stride**: a better version of Titan with full frontend, backend, and integrations.

## Overview

| Layer | Choice |
|--------|--------|
| Frontend | React 19 + Vite 8 |
| Backend | FastAPI only (no Flask) |
| Database | PostgreSQL + pgvector |
| ML / AI | Qwen2.5-1.5B + LoRA, sentence-transformers |
| Deploy | Docker + docker-compose |

---

## Frontend

| Piece | Choice |
|--------|--------|
| Framework | **React 19** |
| Language | **JavaScript (JSX)** (TypeScript optional) |
| Bundler | **Vite 8** + `@vitejs/plugin-react` |
| Styling | Custom CSS (CSS variables, dark/light via `data-theme`) |
| State | React hooks (`useState`, `useEffect`, `useRef`, `useCallback`) |
| HTTP | Native `fetch` (or axios) |
| API client | `src/api/` — base URL, API-KEY headers, shopping/products/system helpers |
| Lint | ESLint + `eslint-plugin-react-hooks` |

---

## Backend

| Piece | Choice |
|--------|--------|
| Language | **Python 3.11** |
| Framework | **FastAPI** (single API — no Flask / flask-restx) |
| Server | **Uvicorn** (optional: Gunicorn + Uvicorn workers in production) |
| Validation / docs | **Pydantic v2** — OpenAPI at `/docs` and `/redoc` |
| CORS | `fastapi.middleware.cors` |
| Config | **python-dotenv** + settings class |
| Auth | Shared **API key** header (`API-KEY`) |
| HTTP client | **httpx** or **requests** (model / external calls) |

---

## Database & search

| Piece | Choice |
|--------|--------|
| Database | **PostgreSQL** |
| Vectors | **pgvector** (384-dim embeddings, HNSW index) |
| Driver | **psycopg2-binary** (or **asyncpg** if fully async) |
| Search | Hybrid: keyword SQL filters + semantic vector similarity |

---

## ML / AI

| Piece | Choice |
|--------|--------|
| LLM | **Qwen2.5-1.5B-Instruct** + **LoRA** (PEFT) |
| Runtime | **PyTorch** + **transformers** + **peft** |
| Embeddings | **sentence-transformers** — `all-MiniLM-L6-v2` |
| Placement | In-process under FastAPI `services/` / `ml/`, or a second FastAPI worker if memory is limited |

---

## API integrations (FE ↔ BE)

Prefix: `/api/v1`

| Feature | Method | Path |
|---------|--------|------|
| Health | `GET` | `/system/health` |
| Parse query | `POST` | `/shopping/parse-query` |
| Search | `POST` | `/shopping/search` |
| Smart search | `POST` | `/shopping/smart-search` |
| Categories | `GET` | `/products/categories` |

---

## DevOps / deploy

| Piece | Choice |
|--------|--------|
| Containers | **Docker** + **docker-compose** (API + Postgres with pgvector) |
| Hosting | Render or any Docker host (thin API if models stay local) |
| Env | `.env` / `.env.example` |

---

## Training (optional)

| Piece | Choice |
|--------|--------|
| Trainer | Hugging Face + PEFT LoRA |
| Format | ChatML |
| Output | LoRA adapters under `training/outputs/` |

---

## One-line summary

**React 19 + Vite** frontend · **FastAPI + Pydantic + Uvicorn** backend · **PostgreSQL + pgvector** · **Qwen LoRA + MiniLM embeddings** · **Docker**.
