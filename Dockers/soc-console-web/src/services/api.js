const API_BASE = import.meta.env.VITE_API_BASE || "http://localhost:7000";

async function httpJson(url, opts) {
  console.log("[API] ->", url, opts ?? {});
  const r = await fetch(url, opts);
  const txt = await r.text();

  console.log("[API] <-", url, "status:", r.status, "body:", txt.slice(0, 400));

  if (!r.ok) throw new Error(txt);

  try {
    return JSON.parse(txt);
  } catch (e) {
    console.error("[API] JSON parse failed:", url, e);
    throw e;
  }
}

export function fetchAlerts(params = {}) {
  const usp = new URLSearchParams(params);
  return httpJson(`${API_BASE}/alerts?${usp.toString()}`);
}

export function fetchAlert(alertId) {
  return httpJson(`${API_BASE}/alerts/${alertId}`);
}

export function fetchEvents(alertId) {
  return httpJson(`${API_BASE}/alerts/${alertId}/events`);
}

export function postDecision(alertId, body) {
  return httpJson(`${API_BASE}/alerts/${alertId}/decision`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  });
}

export function fetchOperator(operatorId) {
  return httpJson(`${API_BASE}/operators/${operatorId}`);
}

export function fetchOperators(params = {}) {
  const usp = new URLSearchParams(params);
  return httpJson(`${API_BASE}/operators?${usp.toString()}`);
}

export function getApiBase() {
  return API_BASE;
}

export async function fetchOperatorSla(operatorId, params = {}) {
  const qs = new URLSearchParams({
    limit: String(params.limit ?? 50),
    offset: String(params.offset ?? 0),
  });

  const url = `${API_BASE}/operators/${operatorId}/sla?${qs.toString()}`;
  return httpJson(url);
}

export function fetchSocMetrics(params = {}) {
  const usp = new URLSearchParams({
    days: String(params.days ?? 7),
  });
  return httpJson(`${API_BASE}/soc/metrics?${usp.toString()}`);
}

export function postRetrain(payload) {
  return httpJson(`${API_BASE}/retrain`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
  });
}
export async function createTrainingSession({ config, total_questions }) {
  const r = await fetch(`${API_BASE}/training/sessions`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ config, total_questions }),
  });
  if (!r.ok) throw new Error(await r.text());
  return r.json();
}

export async function fetchTrainingNext(sessionId) {
  const r = await fetch(`${API_BASE}/training/sessions/${sessionId}/next`);
  if (!r.ok) throw new Error(await r.text());
  return r.json();
}

export async function submitTrainingAnswer(sessionId, payload) {
  const r = await fetch(`${API_BASE}/training/sessions/${sessionId}/answer`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
  });
  if (!r.ok) throw new Error(await r.text());
  return r.json();
}

export async function finishTrainingSession(sessionId) {
  const r = await fetch(`${API_BASE}/training/sessions/${sessionId}/finish`, { method: "POST" });
  if (!r.ok) throw new Error(await r.text());
  return r.json();
}

export async function fetchTrainingSession(sessionId) {
  const r = await fetch(`${API_BASE}/training/sessions/${sessionId}`);
  if (!r.ok) throw new Error(await r.text());
  return r.json();
}

export async function fetchTrainingSessions() {
  const r = await fetch(`${API_BASE}/training/sessions`);
  if (!r.ok) throw new Error(await r.text());
  return r.json();
}

export async function fetchMlModels() {
  const r = await fetch(`${API_BASE}/ml/models`);
  if (!r.ok) throw new Error(`fetchMlModels failed: ${r.status}`);
  return r.json();
}

export async function fetchMlModelDetail(version) {
  const r = await fetch(`${API_BASE}/ml/models/${encodeURIComponent(version)}`);
  if (!r.ok) throw new Error(`fetchMlModelDetail failed: ${r.status}`);
  return r.json();
}