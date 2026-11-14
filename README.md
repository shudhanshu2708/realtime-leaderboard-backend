# Real-Time Leaderboard

A live leaderboard app. Players register, submit scores, and see the top 10 update instantly.

**Stack:** FastAPI, MySQL, Redis, JWT, Server-Sent Events (backend) · React + Vite (frontend)

## Features
- Register and log in (JWT)
- Submit points and see your rank
- Live top 10 with Server-Sent Events
- Rate limiting on login, register and score endpoints

## Run it

**1. Start MySQL and Redis**
```bash
docker compose up -d
```

**2. Backend** (http://localhost:8080/docs)
```bash
pip install -r requirements.txt
cp .env.example .env        # set JWT_SECRET to a long random value
uvicorn app.main:app --reload --reload-dir app --port 8080
```

**3. Frontend** (http://localhost:5173)
```bash
cd frontend
npm install
npm run dev
```
Needs Node.js 20.19+ or 22.12+.

## Tests
```bash
pip install -r requirements-dev.txt
pytest
```

## API
| Method | Path | Auth |
|---|---|---|
| POST | `/api/auth/register` | no |
| POST | `/api/auth/login` | no |
| POST | `/api/scores` | yes |
| GET | `/api/leaderboard` | no |
| GET | `/api/leaderboard/me` | yes |
| GET | `/api/leaderboard/stream` | no (live updates) |

## Known limitations
- Live updates work on a single server instance only
- Equal scores have no defined tie-break
- Scores are submitted by the client (a real app would use server-side events)
