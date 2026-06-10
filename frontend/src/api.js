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

export async function apiPatch(path, body) {
  const r = await fetch(`${API}${path}`, {
    method: "PATCH",
    credentials: "include",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  });
  const data = await r.json();
  if (!r.ok) throw new Error(data.error || "Ошибка");
  return data;
}

export async function downloadApiFile(path, filename) {
  const r = await fetch(`${API}${path}`, { credentials: "include" });
  if (!r.ok) {
    let msg = "Ошибка скачивания";
    try {
      const data = await r.json();
      if (data?.error) msg = data.error;
    } catch {
      /* not json */
    }
    throw new Error(msg);
  }
  const blob = await r.blob();
  const url = URL.createObjectURL(blob);
  const a = document.createElement("a");
  a.href = url;
  a.download = filename;
  document.body.appendChild(a);
  a.click();
  a.remove();
  URL.revokeObjectURL(url);
}

export async function apiUpload(path, formData) {
  const r = await fetch(`${API}${path}`, {
    method: "POST",
    credentials: "include",
    body: formData,
  });
  return r.json();
}
