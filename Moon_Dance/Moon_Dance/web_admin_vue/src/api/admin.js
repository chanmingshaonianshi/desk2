const TOKEN_KEY = "adminToken";
const API_KEY_KEY = "adminApiKey";

export function getStoredAuth() {
  return {
    token: localStorage.getItem(TOKEN_KEY) || "",
    apiKey: localStorage.getItem(API_KEY_KEY) || "myh",
  };
}

export function saveAuth({ token, apiKey }) {
  if (token) localStorage.setItem(TOKEN_KEY, token);
  if (apiKey) localStorage.setItem(API_KEY_KEY, apiKey);
}

export function clearAuth() {
  localStorage.removeItem(TOKEN_KEY);
}

async function parseResponse(response) {
  const payload = await response.json().catch(() => ({}));
  if (!response.ok || !payload.ok) {
    throw new Error(payload.message || `请求失败：${response.status}`);
  }
  return payload.data;
}

export async function loginAdmin({ username, password, apiKey }) {
  const response = await fetch("/api/admin/login", {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
      "X-API-Key": apiKey,
    },
    body: JSON.stringify({ username, password }),
  });
  return parseResponse(response);
}

export function createAdminApi({ token, apiKey }) {
  const headers = {
    "Content-Type": "application/json",
    "X-API-Key": apiKey,
    Authorization: `Bearer ${token}`,
  };

  const get = async (url) => {
    const response = await fetch(url, { headers });
    return parseResponse(response);
  };

  return {
    summary: () => get("/api/admin/summary"),
    devices: () => get("/api/admin/devices"),
    regions: () => get("/api/admin/regions"),
    analytics: (days) => get(`/api/admin/analytics?days=${days}`),
    users: () => get("/api/admin/users"),
  };
}
