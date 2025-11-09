# EthiCo Live Compliance Copilot

This repository contains the real-time EthiCo MVP that streams live agent calls, raises FDCPA / Reg F alerts, and stores every session in MongoDB. It also includes the **Admin Dashboard** used by supervisors for historical review.

```
UB_hacking/
├── backend/            # Flask + Socket.IO API, Gemini + Mongo orchestration
├── frontend/           # React dashboard (live transcript + alerts)
├── AdminDashboard/     # Supervisor portal (agent search, transcripts, AI chat)
└── project_spec.md     # Case study notes
```

## Prerequisites
- Python 3.11+
- Node.js 20+
- MongoDB Atlas (or local MongoDB instance)
- ElevenLabs + Google Gemini API keys (see `.env.example`)

---

## 1. Run the Live MVP (frontend + backend)

1. **Environment variables**
   ```bash
   cp .env.example .env            # root-level file used by both services
   # fill in MONGO_URI, GEMINI keys, ELEVENLABS key, SERPAPI_KEY, etc.
   ```

2. **Backend**
   ```bash
   cd backend
   python3 -m venv .venv && source .venv/bin/activate
   pip install -r requirements.txt
   flask run --app app.py  # or python app.py to use Socket.IO dev server
   ```
   *Default port: `http://127.0.0.1:5000`*

3. **Frontend**
   ```bash
   cd ../frontend
   npm install
   npm run dev -- --host 0.0.0.0 --port 5173 
   ```
   *Vite serves the dashboard on `http://127.0.0.1:5173` (uses `VITE_API_URL`).*

4. **Upload / Simulation Mode**
   - Use the “Upload Recording” tab to analyze historical audio. The backend creates a session + call record automatically so it appears in the dashboard.
   - Simulation allows you to paste a transcript, stream it live for demos, and still receive Gemini compliance analysis + stored warnings.

---

## 2. Admin Dashboard (Supervisor Portal)
The `AdminDashboard/` subproject is a standalone stack that shares MongoDB with the MVP. Supervisors can search agents, replay transcripts, and chat with an AI bot grounded on each call.

### Quick Start
```bash
cd AdminDashboard
cp .env.example .env        # configure Mongo + LLM keys
make dev                    # builds docker-compose stack (frontend, backend, Mongo, mongo-express)
make seed                   # optional: populate demo data (requires ALLOW_DEV_SEED=true)
```
- UI: `http://localhost:5173`
- API: `http://localhost:8000`

### Useful Admin Commands
| Command | Description |
| --- | --- |
| `make dev` | Build + start the Docker stack |
| `make down` | Stop the stack |
| `make seed` | Seed Mongo with demo agents/calls |
| `make fmt` | Run formatters (Prettier + Ruff) |
| `make test` | Run frontend Vitest + backend Pytest |
| `curl -X POST http://localhost:8000/api/dev/seed` | Seed via API when `ALLOW_DEV_SEED=true` |

### Folder Highlights
- `AdminDashboard/frontend/` — Vite + Tailwind UI with chat shell, command palette, keyboard shortcuts.
- `AdminDashboard/backend/` — Flask blueprints (`/agents`, `/calls`, `/ai`) + Socket.IO for streaming AI answers.
- `infra/docker-compose.yml` — local dev stack with Mongo + mongo-express.

---

## Tips
- When both dashboards point to the same MongoDB URI, live calls, uploads, and admin insights stay in sync automatically.
- To avoid duplicate Gemeni traffic, cache KB summaries via `KB_SUMMARY_TTL_SECONDS` in `.env`.
- `npm run lint` (frontend) and `python -m py_compile backend/app.py` are good quick checks before shipping changes.

Happy hacking!
