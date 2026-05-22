const API = "/api";

export async function apiGet(path) {
  const r = await fetch(`${API}${path}`, { credentials: "include" });
  return r.json();
}

export async function apiPost(path, body) {
  const r = await fetch(`${API}${path}`, {
    method: "POST",
    credentials: "include",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  });
  const data = await r.json();
  if (!r.ok) throw new Error(data.error || "Ошибка");
  return data;
}

export async function apiUpload(path, formData) {
  const r = await fetch(`${API}${path}`, {
    method: "POST",
    credentials: "include",
    body: formData,
  });
  return r.json();
}
