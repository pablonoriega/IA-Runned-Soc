export function severityTone(sev) {
  if (sev >= 5) return "red";
  if (sev === 4) return "pink";
  if (sev === 3) return "orange";
  if (sev === 2) return "green";
  return "cyan";
}

export function statusTone(status) {
  if (status === "ALL") return "lilac";
  if (status === "PROCESSING") return "orange";
  if (status === "PENDING_HUMAN") return "blue";
  if (status === "CLOSED") return "red";
  return "white";
}

export function dotColorForTone(tone) {
  switch (tone) {
    case "red": return "#ef4444";
    case "orange": return "#f97316";
    case "green": return "#22c55e";
    case "blue": return "#3b82f6";
    case "pink": return "#ec4899";
    case "lilac": return "#a855f7";
    case "cyan": return "#06b6d4";
    case "white": return "#e2e8f0";
    default: return "#0f172a";
  }
}