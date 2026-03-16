
export const ASSET_TYPES = ["workstation", "server", "database", "cloud_service"];

export const STATUS_OPTIONS = [
  { value: "ALL", label: "All" },
  { value: "PROCESSING", label: "PROCESSING" },
  { value: "PENDING_HUMAN", label: "PENDING_HUMAN" },
  { value: "CLOSED", label: "CLOSED" },
];

export function normStatus(s) {
  return String(s ?? "").toUpperCase().trim().replace(/\s+/g, "_");
}

export function statusTone(status) {
  const s = normStatus(status);
  if (s === "PROCESSING") return "blue";
  if (s === "PENDING_HUMAN") return "amber";
  if (s === "CLOSED") return "slate";
  return "violet";
}

export function assetTone(activeCount) {
  if (activeCount <= 0) return "ok";
  if (activeCount <= 1) return "low";
  if (activeCount <= 3) return "mid";
  if (activeCount <= 6) return "high";
  return "crit";
}

export function sevTone(sev) {
  const n = Number(sev ?? 0);
  if (n >= 5) return "red";
  if (n === 4) return "rose";
  if (n === 3) return "amber";
  if (n === 2) return "green";
  return "cyan";
}

export function fmtAsset(t) {
  const map = {
    workstation: "Workstation",
    server: "Server",
    database: "Database",
    cloud_service: "Cloud service",
  };
  return map[t] ?? t;
}

export function humanizeToken(s) {
  const x = String(s ?? "").replace(/[_-]+/g, " ").trim();
  if (!x) return "-";
  return x.charAt(0).toUpperCase() + x.slice(1);
}

/* -----------------------------
   Capacity (CON % y thresholds)
   <30% green, 30-70 amber, >70 red
------------------------------ */
export function calcCapacity(operator) {
  const assigned = Number(operator?.active_assigned ?? 0);
  const max = Number(operator?.max_active ?? 0);

  if (!Number.isFinite(max) || max <= 0) {
    return { assigned, max: max || 0, pct: null };
  }

  const pct = Math.max(0, Math.min(100, Math.round((assigned / max) * 100)));
  return { assigned, max, pct };
}

export function capacityTone(pct) {
  if (pct == null) return "slate";
  if (pct < 30) return "green";
  if (pct <= 70) return "amber";
  return "red";
}

export function capacityLabel(assigned, max, pct) {
  if (!max) return `load ${assigned}/-`;
  return `load ${assigned}/${max} (${pct}%)`;
}

/* -----------------------------
   SLA helpers
------------------------------ */

function parseTs(x) {
  if (!x) return null;
  const s = String(x).trim();

  const m = s.match(
    /^(\d{4}-\d{2}-\d{2})\s+(\d{2}:\d{2}:\d{2}(?:\.\d+)?)\s*([+-]\d{2})(\d{2})$/
  );
  if (m) {
    const d = new Date(`${m[1]}T${m[2]}${m[3]}:${m[4]}`);
    return Number.isNaN(d.getTime()) ? null : d;
  }

  const d = new Date(s);
  return Number.isNaN(d.getTime()) ? null : d;
}

function diffSeconds(a, b) {
  const da = parseTs(a);
  const db = parseTs(b);
  if (!da || !db) return null;
  return Math.max(0, Math.round((da.getTime() - db.getTime()) / 1000));
}

export function fmtDuration(sec) {
  if (sec == null) return "-";

  const s = Math.max(0, Number(sec) || 0);

  const h = Math.floor(s / 3600);
  const m = Math.floor((s % 3600) / 60);
  const r = s % 60;

  const formatSeconds = (value) => {
    return Number.isInteger(value)
      ? value
      : value.toFixed(2);
  };

  if (h > 0) return `${h}h ${m}m`;
  if (m > 0) return `${m}m ${formatSeconds(r)}s`;
  return `${formatSeconds(r)}s`;
}

export function calcResolveSlaSeconds(alert) {
  if (normStatus(alert?.status) !== "CLOSED") return null;
  const assignedAt = alert?.assigned_at ?? null;
  const closedAt = alert?.closed_at ?? null;
  if (!assignedAt || !closedAt) return null;
  return diffSeconds(closedAt, assignedAt);
}

export function resolveOk(resolveSec, operator) {
  if (resolveSec == null) return false;
  const target = Number(operator?.sla_resolve_seconds ?? 0);
  if (!Number.isFinite(target) || target <= 0) return false;
  return resolveSec <= target;
}