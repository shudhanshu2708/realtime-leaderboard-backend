# Leaderboard Frontend (React + Vite)

Frontend for the FastAPI leaderboard backend.

## Run
1. Start the backend (`uvicorn app.main:app --port 8080`, with MySQL + Redis running).
2. In this folder:
   ```bash
   npm install
   npm run dev
   ```
3. Open http://localhost:5173

The backend URL defaults to `http://localhost:8080`. To change it, copy `.env.example` to `.env`
and edit `VITE_API_URL`. If your frontend runs on another origin, add it to `CORS_ORIGINS` in the backend.

## Features
- Top navbar with live connection status and signed-in user
- Hero stats: current leader, top score, your position
- Top-3 podium plus a ranked table with avatars and score meters
- Rows flash green when a player's score goes up in real time (SSE)
- Sign-in / create-account tabs; JWT kept in `localStorage`, auto logout when it expires
- Account panel: your rank, score, and points needed to pass the player above you
- Quick-add buttons (+10 / +50 / +100 / +500), toast confirmations, loading skeletons, empty state
- Light and dark mode, responsive, keyboard-focus styles, reduced-motion support

## Structure
```text
src/
├── main.jsx    entry
├── App.jsx     leaderboard (SSE), auth card, account panel
├── api.js      fetch helper + endpoints
└── styles.css
```
