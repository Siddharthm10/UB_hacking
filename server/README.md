Server quickstart

- Copy `server/.env.example` to `server/.env` and set `MONGODB_URI`:

  MONGODB_URI=mongodb+srv://admin:adminrrc@cluster0.vkmernd.mongodb.net/?appName=Cluster0
  PORT=4000

- Install deps and run:

  cd server
  npm install
  npm run dev

- Seed demo data:

  curl -X POST http://localhost:4000/api/calls/seed

Frontend integration

- In `my-dashboard`, set the API URL (optional). Create `my-dashboard/.env.local` with:

  VITE_API_URL=http://localhost:4000

- Start the app:

  cd my-dashboard
  npm install
  npm run dev

- The UI will load data from the API if reachable; otherwise it falls back to mock data and a simulated transcript.

