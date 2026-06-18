const BASE = "http://localhost:8001/api";

async function request<T>(path: string, options: RequestInit = {}): Promise<T> {
  const token =
    typeof window !== "undefined" ? localStorage.getItem("token") : null;

  const headers: Record<string, string> = {
    "Content-Type": "application/json",
    ...(options.headers as Record<string, string>),
  };
  if (token) {
    headers["Authorization"] = `Bearer ${token}`;
  }

  console.log(`[API] ${options.method || "GET"} ${path} | token: ${token ? "present" : "MISSING"}`);

  const res = await fetch(`${BASE}${path}`, { ...options, headers });

  if (!res.ok) {
    const body = await res.json().catch(() => ({ detail: res.statusText }));
    const detail = body.detail || `Erro ${res.status}`;
    console.error(`[API] ${res.status} ${path}:`, detail);
    throw new Error(detail);
  }

  return res.json();
}

export const api = {
  get: <T>(path: string) => request<T>(path),

  post: <T>(path: string, data?: unknown) =>
    request<T>(path, { method: "POST", body: JSON.stringify(data) }),

  patch: <T>(path: string, data?: unknown) =>
    request<T>(path, { method: "PATCH", body: JSON.stringify(data) }),

  delete: <T>(path: string) => request<T>(path, { method: "DELETE" }),
};
