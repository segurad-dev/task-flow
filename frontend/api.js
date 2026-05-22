// Central fetch wrapper — attaches base URL and Bearer token automatically.
// All functions throw an Error with a human-readable message on non-2xx responses.

async function apiFetch(path, options = {}) {
  const token = localStorage.getItem("token");

  const headers = { "Content-Type": "application/json", ...options.headers };
  if (token) headers["Authorization"] = `Bearer ${token}`;

  const res = await fetch(API_BASE_URL + path, { ...options, headers });

  if (res.status === 204) return null;

  // Auto-logout on expired/invalid token — dashboard listens for this event
  if (res.status === 401) {
    window.dispatchEvent(new CustomEvent("unauthorized"));
    throw new Error("Сессия истекла. Войдите снова.");
  }

  const data = await res.json();

  if (!res.ok) {
    const detail = data?.detail;
    if (typeof detail === "string") throw new Error(detail);
    // Pydantic validation errors return an array of objects
    if (Array.isArray(detail)) throw new Error(detail.map(e => e.msg).join("; "));
    throw new Error(`HTTP ${res.status}`);
  }

  return data;
}

// ── Auth ──────────────────────────────────────────────────────────────────────

async function login(email, password) {
  // /auth/login expects form-encoded data (OAuth2PasswordRequestForm), not JSON
  const body = new URLSearchParams({ username: email, password });
  const res = await fetch(API_BASE_URL + "/auth/login", {
    method: "POST",
    body,
  });
  const data = await res.json();
  if (!res.ok) {
    const detail = data?.detail;
    throw new Error(typeof detail === "string" ? detail : `HTTP ${res.status}`);
  }
  return data; // { access_token, token_type }
}

async function register(email, username, password) {
  return apiFetch("/auth/register", {
    method: "POST",
    body: JSON.stringify({ email, username, password }),
  });
}

// ── Projects ──────────────────────────────────────────────────────────────────

async function getProjects() {
  return apiFetch("/projects/");
}

async function createProject(title, description = "") {
  return apiFetch("/projects/", {
    method: "POST",
    body: JSON.stringify({ title, description }),
  });
}

// ── Tasks ─────────────────────────────────────────────────────────────────────

async function getTasks(status = null) {
  const params = new URLSearchParams({ limit: "100" });
  if (status) params.set("status", status);
  return apiFetch(`/tasks/?${params}`);
}

async function createTask(title, description, projectId, assigneeId) {
  return apiFetch("/tasks/", {
    method: "POST",
    body: JSON.stringify({
      title,
      description: description || null,
      project_id: projectId,
      assignee_id: assigneeId,
    }),
  });
}

async function updateTask(id, data) {
  return apiFetch(`/tasks/${id}`, {
    method: "PATCH",
    body: JSON.stringify(data),
  });
}

async function deleteTask(id) {
  return apiFetch(`/tasks/${id}`, { method: "DELETE" });
}

// ── Analytics ─────────────────────────────────────────────────────────────────

async function getProjectAnalytics(projectId) {
  return apiFetch(`/analytics/project/${projectId}`);
}
