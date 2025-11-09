EthiCo Live — Real‑time Call Monitoring Dashboard

Overview

- Frontend: React + Vite + Tailwind (folder: my-dashboard)
- Backend: Flask + MongoDB (folder: backend)
- Purpose: Monitor live calls for compliance & empathy with a ChatGPT‑style transcript UI and call health status (GREEN/RED).

Backend — Flask

1) Setup Python env
   cd backend
   python -m venv .venv
   .\.venv\Scripts\activate   # on Windows PowerShell
   pip install -r requirements.txt

2) Configure env
   Copy .env.example to .env and set MONGODB_URI (Atlas or local). Optionally set FLASK_PORT (default 5000).

3) Run API
   python -m backend.app

   Health: http://localhost:5000/health
   Current call: http://localhost:5000/api/call/current

   The backend seeds a sample call (callId CID-0001) on first run.

4) (Optional) Append a live transcript line
   PowerShell example:
   Invoke-RestMethod -Uri http://localhost:5000/api/call/CID-0001/transcript -Method Post -Body (@{ speaker='agent'; text='We need payment immediately or else.' } | ConvertTo-Json) -ContentType 'application/json'

Frontend — React

1) Install & run
   cd my-dashboard
   npm install
   npm run dev

2) Open the app
   http://localhost:5173

Notes

- Vite dev proxy is configured to send /api requests to http://localhost:5000.
- The UI polls the backend every 3 seconds and auto‑scrolls the transcript.
- Status pill turns RED if the backend detects aggressive/shouting phrases in recent agent messages.

