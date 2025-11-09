EthiCo Live — Flask Backend

Setup

1) Create a virtualenv (recommended)
   python -m venv .venv
   .\.venv\Scripts\activate   # PowerShell on Windows

2) Install dependencies
   pip install -r requirements.txt

3) Configure environment
   Copy .env.example to .env and set MONGODB_URI (Atlas or local)
   Optionally set FLASK_PORT (default 5000)

4) Run the API
   python -m backend.app

Endpoints

- GET /api/call/current — latest call with computed status
- GET /api/call/<id> — specific call by callId
- POST /api/call/<id>/transcript — append a transcript line

Seeding

The app seeds a sample call with callId CID-0001 on startup if none exists.

