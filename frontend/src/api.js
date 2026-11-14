export const BASE = import.meta.env.VITE_API_URL || "http://localhost:8080";

export class ApiError extends Error {
  constructor(message, status) {
    super(message);
    this.status = status;
  }
}

async function request(path, { method = "GET", body, token } = {}) {
  let res;
  try {
    res = await fetch(BASE + path, {
      method,
      headers: {
        ...(body ? { "Content-Type": "application/json" } : {}),
        ...(token ? { Authorization: `Bearer ${token}` } : {}),
      },
      body: body ? JSON.stringify(body) : undefined,
    });
  } catch {
    throw new ApiError("Cannot reach the server. Check that the backend is running.", 0);
  }
  const data = await res.json().catch(() => null);
  if (!res.ok) {
    const msg = data?.message || data?.error || `Request failed (${res.status})`;
    throw new ApiError(msg, res.status);
  }
  return data;
}

export const api = {
  register: (username, password) => request("/api/auth/register", { method: "POST", body: { username, password } }),
  login: (username, password) => request("/api/auth/login", { method: "POST", body: { username, password } }),
  addScore: (points, token) => request("/api/scores", { method: "POST", body: { points }, token }),
  me: (token) => request("/api/leaderboard/me", { token }),
  top: (n) => request(`/api/leaderboard/top/${n}`),
};
