const BASE = "http://localhost:8001/api";

async function request<T>(path: string, options: RequestInit = {}, timeoutMs = 120000): Promise<T> {
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

  const controller = new AbortController();
  const timer = setTimeout(() => controller.abort(), timeoutMs);
  const res = await fetch(`${BASE}${path}`, { ...options, headers, signal: controller.signal }).finally(() => clearTimeout(timer));

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

  post: <T>(path: string, data?: unknown, timeoutMs?: number) =>
    request<T>(path, { method: "POST", body: JSON.stringify(data) }, timeoutMs),

  patch: <T>(path: string, data?: unknown) =>
    request<T>(path, { method: "PATCH", body: JSON.stringify(data) }),

  delete: <T>(path: string) => request<T>(path, { method: "DELETE" }),

  postSSE: async (
    path: string,
    data: unknown,
    onProgress: (ev: { current?: number; total?: number; name?: string; done?: boolean; message?: string; error?: string }) => void,
  ): Promise<void> => {
    const token = typeof window !== "undefined" ? localStorage.getItem("token") : null;
    const headers: Record<string, string> = { "Content-Type": "application/json" };
    if (token) headers["Authorization"] = `Bearer ${token}`;
    const res = await fetch(`${BASE}${path}`, { method: "POST", headers, body: JSON.stringify(data) });
    if (!res.ok) {
      const body = await res.json().catch(() => ({ detail: res.statusText }));
      throw new Error(body.detail || `Erro ${res.status}`);
    }
    const reader = res.body?.getReader();
    if (!reader) throw new Error("Sem suporte a streaming.");
    const decoder = new TextDecoder();
    let buffer = "";
    while (true) {
      const { done, value } = await reader.read();
      if (done) break;
      buffer += decoder.decode(value, { stream: true });
      const lines = buffer.split("\n");
      buffer = lines.pop() || "";
      for (const line of lines) {
        if (line.startsWith("data: ")) {
          try { onProgress(JSON.parse(line.slice(6))); } catch {}
        }
      }
    }
    if (buffer.startsWith("data: ")) {
      try { onProgress(JSON.parse(buffer.slice(6))); } catch {}
    }
  },

  upload: async <T>(path: string, file: File): Promise<T> => {
    const token = typeof window !== "undefined" ? localStorage.getItem("token") : null;
    const formData = new FormData();
    formData.append("file", file);
    const headers: Record<string, string> = {};
    if (token) headers["Authorization"] = `Bearer ${token}`;
    const res = await fetch(`${BASE}${path}`, { method: "POST", headers, body: formData });
    if (!res.ok) {
      const body = await res.json().catch(() => ({ detail: res.statusText }));
      throw new Error(body.detail || `Erro ${res.status}`);
    }
    return res.json();
  },
};
