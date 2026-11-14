import { useCallback, useEffect, useRef, useState } from "react";
import { api, BASE } from "./api.js";

const fmt = (n) => Number(n).toLocaleString();
const hue = (s) => [...s].reduce((a, c) => (a * 31 + c.charCodeAt(0)) % 360, 7);

/* ---------- small pieces ---------- */
function Avatar({ name, size = 36 }) {
  return (
    <span className="avatar" aria-hidden="true"
          style={{ width: size, height: size, fontSize: size * 0.38, background: `hsl(${hue(name)} 48% 40%)` }}>
      {name.slice(0, 2).toUpperCase()}
    </span>
  );
}

const TrophyIcon = () => (
  <svg width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2"
       strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">
    <path d="M8 21h8M12 17v4M7 4h10v5a5 5 0 0 1-10 0V4Z" />
    <path d="M17 5h3v2a3 3 0 0 1-3 3M7 5H4v2a3 3 0 0 0 3 3" />
  </svg>
);

function LivePill({ live }) {
  return (
    <span className={`pill ${live ? "on" : ""}`} role="status">
      <i /> {live ? "Live" : "Reconnecting…"}
    </span>
  );
}

/* ---------- data hooks ---------- */
function useLeaderboard() {
  const [rows, setRows] = useState(null);
  const [live, setLive] = useState(false);
  useEffect(() => {
    const es = new EventSource(`${BASE}/api/leaderboard/stream`);
    es.onopen = () => setLive(true);
    es.onerror = () => setLive(false); // EventSource reconnects on its own
    es.addEventListener("leaderboard", (e) => { setLive(true); setRows(JSON.parse(e.data)); });
    return () => es.close();
  }, []);
  return { rows, live };
}

// Marks users whose score just went up so their row can flash.
function useBumps(rows) {
  const prev = useRef(new Map());
  const [bumped, setBumped] = useState(new Set());
  useEffect(() => {
    if (!rows) return;
    const changed = new Set();
    rows.forEach((r) => {
      const p = prev.current.get(r.userId);
      if (p !== undefined && r.score > p) changed.add(r.userId);
    });
    prev.current = new Map(rows.map((r) => [r.userId, r.score]));
    if (!changed.size) return;
    setBumped(changed);
    const t = setTimeout(() => setBumped(new Set()), 1500);
    return () => clearTimeout(t);
  }, [rows]);
  return bumped;
}

/* ---------- leaderboard ---------- */
function Podium({ rows, username, bumped }) {
  return (
    <div className="podium">
      {[1, 0, 2].map((i) => {
        const r = rows[i];
        const place = i + 1;
        if (!r) {
          return (
            <div key={place} className={`pod p${place} open`}>
              <span className="medal">{place}</span>
              <p className="pod-name">Open spot</p>
            </div>
          );
        }
        return (
          <div key={r.userId} className={`pod p${place} ${r.username === username ? "mine" : ""} ${bumped.has(r.userId) ? "bump" : ""}`}>
            <span className="medal">{place}</span>
            <Avatar name={r.username} size={place === 1 ? 64 : 52} />
            <p className="pod-name">{r.username}{r.username === username && <em>You</em>}</p>
            <p className="pod-score">{fmt(r.score)}<small>pts</small></p>
          </div>
        );
      })}
    </div>
  );
}

function Board({ rows, username }) {
  const bumped = useBumps(rows);
  if (rows === null) {
    return (
      <section className="panel" aria-busy="true">
        <div className="skeleton" /><div className="skeleton" /><div className="skeleton" /><div className="skeleton" />
      </section>
    );
  }
  if (rows.length === 0) {
    return (
      <section className="panel empty">
        <TrophyIcon />
        <h3>No scores yet</h3>
        <p>Create an account and add points to take rank 1.</p>
      </section>
    );
  }
  const max = rows[0].score || 1;
  const rest = rows.slice(3);
  return (
    <section className="panel" aria-label="Leaderboard">
      <Podium rows={rows} username={username} bumped={bumped} />
      {rest.length > 0 && (
        <table className="table">
          <thead>
            <tr><th scope="col">Rank</th><th scope="col">Player</th><th scope="col" className="num">Score</th></tr>
          </thead>
          <tbody>
            {rest.map((r) => (
              <tr key={r.userId} className={`${r.username === username ? "mine" : ""} ${bumped.has(r.userId) ? "bump" : ""}`}>
                <td className="rk">{r.rank}</td>
                <td>
                  <div className="player">
                    <Avatar name={r.username} size={32} />
                    <div className="pcell">
                      <span>{r.username}{r.username === username && <em>You</em>}</span>
                      <span className="meter"><span style={{ width: `${Math.max(3, (r.score / max) * 100)}%` }} /></span>
                    </div>
                  </div>
                </td>
                <td className="num">{fmt(r.score)}</td>
              </tr>
            ))}
          </tbody>
        </table>
      )}
    </section>
  );
}

/* ---------- sidebar: auth ---------- */
function AuthCard({ onAuth }) {
  const [mode, setMode] = useState("login");
  const [username, setUsername] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);
  const isLogin = mode === "login";

  async function submit(e) {
    e.preventDefault();
    setError(""); setBusy(true);
    try {
      const { token } = await (isLogin ? api.login : api.register)(username.trim(), password);
      onAuth(token, username.trim());
    } catch (err) {
      setError(err.status === 409 ? "That username is taken. Choose another." : err.message);
    } finally { setBusy(false); }
  }

  return (
    <form className="card" onSubmit={submit}>
      <div className="tabs" role="tablist">
        {["login", "register"].map((m) => (
          <button key={m} type="button" role="tab" aria-selected={mode === m}
                  className={mode === m ? "active" : ""} onClick={() => { setMode(m); setError(""); }}>
            {m === "login" ? "Log in" : "Create account"}
          </button>
        ))}
      </div>
      <p className="lead">{isLogin ? "Log in to submit scores and see your rank." : "Pick a username and start climbing the board."}</p>
      <label>Username
        <input value={username} onChange={(e) => setUsername(e.target.value)} minLength={3} maxLength={40}
               autoComplete="username" required />
      </label>
      <label>Password
        <input type="password" value={password} onChange={(e) => setPassword(e.target.value)}
               minLength={isLogin ? 1 : 8} maxLength={72} autoComplete={isLogin ? "current-password" : "new-password"} required />
      </label>
      {!isLogin && <p className="hint">Use at least 8 characters.</p>}
      {error && <p className="error" role="alert">{error}</p>}
      <button className="btn" disabled={busy}>{busy ? "Please wait…" : isLogin ? "Log in" : "Create account"}</button>
    </form>
  );
}

/* ---------- sidebar: account ---------- */
function Account({ token, username, rows, onLogout, onExpired, onToast }) {
  const [me, setMe] = useState(null);
  const [ahead, setAhead] = useState(null); // the player directly above me
  const [points, setPoints] = useState("");
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);

  const handle = useCallback((err) => (err.status === 401 ? onExpired() : setError(err.message)), [onExpired]);
  const loadMe = useCallback(() => api.me(token).then(setMe).catch(handle), [token, handle]);
  useEffect(() => { loadMe(); }, [loadMe]);

  // Refresh my numbers when anyone's score changes (rows update over SSE).
  useEffect(() => { if (rows) loadMe(); }, [rows, loadMe]);

  useEffect(() => {
    if (!me || me.rank < 2 || me.rank > 101) { setAhead(null); return; }
    api.top(me.rank - 1).then((list) => setAhead(list[list.length - 1] ?? null)).catch(() => setAhead(null));
  }, [me?.rank, me?.score]);

  async function submit(e) {
    e.preventDefault();
    setError(""); setBusy(true);
    try {
      const res = await api.addScore(Number(points), token);
      onToast(`+${fmt(res.added)} points added. You are now rank ${res.rank}.`);
      setPoints(""); loadMe();
    } catch (err) { handle(err); } finally { setBusy(false); }
  }

  const unranked = me && me.rank === 0;
  const gap = ahead && me ? ahead.score - me.score : null;
  const progress = ahead && me ? Math.min(100, (me.score / ahead.score) * 100) : 100;

  return (
    <>
      <div className="card">
        <div className="who-row">
          <Avatar name={username} size={44} />
          <div><h3>{username}</h3><p className="hint">Signed in</p></div>
          <button className="ghost" onClick={onLogout}>Log out</button>
        </div>
        <dl className="mini">
          <div><dt>Rank</dt><dd>{me ? (unranked ? "–" : `#${me.rank}`) : "…"}</dd></div>
          <div><dt>Score</dt><dd>{me ? fmt(me.score) : "…"}</dd></div>
        </dl>
        {unranked && <p className="hint">You are not ranked yet. Add points to join the board.</p>}
        {!unranked && me && me.rank === 1 && <p className="note">You are in first place.</p>}
        {gap !== null && (
          <div>
            <p className="note"><strong>{fmt(gap + 1)} points</strong> to pass {ahead.username} (#{ahead.rank})</p>
            <div className="progress" role="progressbar" aria-valuenow={Math.round(progress)} aria-valuemin="0" aria-valuemax="100">
              <span style={{ width: `${progress}%` }} />
            </div>
          </div>
        )}
      </div>

      <form className="card" onSubmit={submit}>
        <h3>Add points</h3>
        <label>Points
          <input type="number" min="1" max="1000000" step="1" inputMode="numeric" placeholder="1 – 1,000,000"
                 value={points} onChange={(e) => setPoints(e.target.value)} required />
        </label>
        <div className="quick">
          {[10, 50, 100, 500].map((n) => (
            <button type="button" key={n} onClick={() => setPoints(String(n))}>+{n}</button>
          ))}
        </div>
        {error && <p className="error" role="alert">{error}</p>}
        <button className="btn" disabled={busy}>{busy ? "Adding…" : "Add points"}</button>
      </form>
    </>
  );
}

/* ---------- app ---------- */
export default function App() {
  const [session, setSession] = useState(() => {
    try { return JSON.parse(localStorage.getItem("session")) || null; } catch { return null; }
  });
  const [toast, setToast] = useState("");
  const { rows, live } = useLeaderboard();

  const login = (token, username) => {
    const s = { token, username };
    localStorage.setItem("session", JSON.stringify(s));
    setSession(s);
  };
  const logout = useCallback(() => { localStorage.removeItem("session"); setSession(null); }, []);
  const showToast = useCallback((msg) => setToast(msg), []);
  useEffect(() => {
    if (!toast) return;
    const t = setTimeout(() => setToast(""), 3500);
    return () => clearTimeout(t);
  }, [toast]);

  const leader = rows?.[0];
  const mine = rows?.find((r) => r.username === session?.username);

  return (
    <>
      <header className="nav">
        <div className="nav-in">
          <a className="brand" href="/"><TrophyIcon /> Leaderboard</a>
          <div className="nav-right">
            <LivePill live={live} />
            {session && (
              <span className="chip"><Avatar name={session.username} size={26} />{session.username}</span>
            )}
          </div>
        </div>
      </header>

      <section className="hero">
        <div className="hero-in">
          <h1>Global leaderboard</h1>
          <p>Rankings update for every player the moment a score is submitted.</p>
          <div className="stats">
            <div><span>Current leader</span><strong>{leader ? leader.username : "–"}</strong></div>
            <div><span>Top score</span><strong>{leader ? fmt(leader.score) : "–"}</strong></div>
            <div><span>Your position</span><strong>{session ? (mine ? `#${mine.rank}` : "See panel") : "Log in"}</strong></div>
          </div>
        </div>
      </section>

      <main className="shell">
        <Board rows={rows} username={session?.username} />
        <aside className="side">
          {session
            ? <Account {...session} rows={rows} onLogout={logout} onExpired={logout} onToast={showToast} />
            : <AuthCard onAuth={login} />}
        </aside>
      </main>

      <footer className="foot">Real-time leaderboard · React, FastAPI, Redis, MySQL</footer>
      {toast && <div className="toast" role="status">{toast}</div>}
    </>
  );
}
