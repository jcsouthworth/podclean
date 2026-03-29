const BASE = "/api";

async function request(method, path, body) {
  const opts = {
    method,
    headers: body instanceof FormData ? {} : (body ? { "Content-Type": "application/json" } : {}),
    body: body instanceof FormData ? body : (body ? JSON.stringify(body) : undefined),
  };
  const res = await fetch(BASE + path, opts);
  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: res.statusText }));
    throw new Error(err.detail || res.statusText);
  }
  if (res.status === 204) return null;
  return res.json();
}

export const api = {
  get: (path) => request("GET", path),
  post: (path, body) => request("POST", path, body),
  patch: (path, body) => request("PATCH", path, body),
  delete: (path) => request("DELETE", path),
  upload: (path, formData) => request("POST", path, formData),
};
