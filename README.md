# ChatGPT-style Call Review Dashboard

Premium dark-mode dashboard for reviewing agent call histories, exploring transcripts, and chatting with an AI assistant that is grounded on the active call.

## Stack

- **Frontend**: Vite + React (JavaScript), TailwindCSS, shadcn-inspired primitives, Framer Motion, Zustand, TanStack Query, react-hook-form + zod, Socket.IO client.
- **Backend**: Flask + Flask-SocketIO, MongoDB (pymongo), Pydantic validation, streaming AI abstraction with provider toggle.
- **Infra**: Docker Compose (frontend, backend, MongoDB, mongo-express), Makefile utilities, seed scripts, Vitest + Testing Library, Pytest.

## Getting Started

```bash
cp .env.example .env
# fill in Mongo/OpenAI credentials as needed

# Start everything
make dev

# In another shell, seed demo data
make seed
```

Visit http://localhost:5173 for the UI (backend on http://localhost:8000, Mongo on 27017, mongo-express on 8081).

### Useful Commands

| Command            | Description                                        |
| ------------------ | -------------------------------------------------- |
| `make dev`         | Build + start docker-compose stack                 |
| `make down`        | Stop stack                                         |
| `make seed`        | Populate Mongo with rich demo data                 |
| `make fmt`         | Run prettier + ruff formatters                     |
| `make test`        | Run backend Pytest + frontend Vitest suites        |
| `docker compose -f infra/docker-compose.yml logs -f backend` | Tail backend logs |
| `curl -X POST http://localhost:8000/api/dev/seed` | Seed via API when `ALLOW_DEV_SEED=true` |

## Frontend Highlights

- ChatGPT-inspired shell: collapsible sidebar with agent search, infinite call list, keyboard shortcuts (`/`, `j/k`, `Cmd+K`).
- Virtualized transcript view with sticky header, sentiment + risk pills, and JSON link placeholder.
- AI chat composer with prompt chips, real-time Socket.IO token streaming + HTTP fallback, loading dots, and conversation history.
- Zustand-powered UI preference persistence (agent, sidebar, prompts).
- Comprehensive dark theme via Tailwind, subtle glassmorphism, and Framer Motion micro-interactions.

## Backend Highlights

- Flask blueprints for agents, calls, AI, and dev seed endpoints.
- Mongo indexes ensured at boot; Pydantic request validation; SSE + Socket.IO streaming responses.
- Provider-agnostic LLM interface with guardrails and environment toggles (`LLM_PROVIDER`, `OPENAI_API_KEY`).
- Health/version routes plus automated seed endpoint (`/api/dev/seed`) gated by `ALLOW_DEV_SEED`.

## Testing

- **Backend**: Pytest with mongomock fixtures for calls + AI streaming endpoints.
- **Frontend**: Vitest + Testing Library cover sidebar loading, dashboard rendering, and AI streaming UI.

## Project Layout

```
root/
  frontend/   # Vite app (JS)
  backend/    # Flask API + Socket.IO
  infra/      # docker-compose, seed tooling
  Makefile
  .env.example
```

## Next Steps

- Plug in a real LLM provider inside `backend/api/llm.py`.
- Add analytics drawer charts (Recharts) and PDF export.
- Persist AI Q&A history per call back to Mongo.
