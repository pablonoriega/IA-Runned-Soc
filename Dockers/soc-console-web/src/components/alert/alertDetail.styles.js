export const ui = {
  page: { padding: 16 },
  topRow: { display: "flex", alignItems: "center", justifyContent: "space-between", gap: 12, flexWrap: "wrap" },
  back: {
    padding: "8px 12px",
    borderRadius: 12,
    border: "1px solid rgba(15,23,42,.12)",
    background: "#fff",
    cursor: "pointer",
    fontWeight: 800,
  },
  header: {
    borderRadius: 18,
    padding: 14,
    background: "linear-gradient(135deg, #0b1220 0%, #111b31 100%)",
    color: "#fff",
    border: "1px solid rgba(255,255,255,.08)",
    boxShadow: "0 12px 30px rgba(0,0,0,.18)",
    marginTop: 12,
  },
  title: { fontSize: 20, fontWeight: 900, margin: 0 },
  sub: { opacity: 0.75, fontSize: 12, marginTop: 6 },

  grid: { display: "grid", gridTemplateColumns: "1fr 1fr", gap: 12, marginTop: 12 },

  card: {
    background: "#fff",
    borderRadius: 16,
    padding: 14,
    border: "1px solid rgba(15,23,42,.08)",
    boxShadow: "0 12px 24px rgba(15,23,42,.08)",
  },

  h3: { margin: "0 0 10px 0", fontSize: 14, letterSpacing: 0.2, color: "#0f172a" },

  kv: {
    display: "grid",
    gridTemplateColumns: "1fr",
    gap: "10px 0",
    fontSize: 13,
    color: "#0f172a",
  },

  aiBox: {
    marginTop: 12,
    padding: 12,
    borderRadius: 14,
    border: "1px solid rgba(15,23,42,.08)",
    background: "#f8fafc",
  },
  aiText: {
    fontSize: 13,
    lineHeight: 1.35,
    color: "#0f172a",
    whiteSpace: "pre-wrap",
    wordBreak: "break-word",
  },
  aiEmpty: { color: "#64748b", fontSize: 13, fontWeight: 700 },
  key: { color: "#475569", fontWeight: 700 },
  val: { fontWeight: 700 },

  badge: (tone) => {
    const map = {
      slate: { bg: "rgba(15,23,42,.08)", fg: "#0f172a", br: "rgba(15,23,42,.12)" },

      mint: { bg: "rgba(16,185,129,.10)", fg: "#065f46", br: "rgba(16,185,129,.22)" },
      green:{ bg: "rgba(34,197,94,.14)",  fg: "#166534", br: "rgba(34,197,94,.25)" },
      amber:{ bg: "rgba(245,158,11,.16)", fg: "#92400e", br: "rgba(245,158,11,.28)" },
      rose: { bg: "rgba(244,63,94,.12)",  fg: "#9f1239", br: "rgba(244,63,94,.24)" },
      red:  { bg: "rgba(239,68,68,.16)",  fg: "#991b1b", br: "rgba(239,68,68,.32)" },

      blue:  { bg: "rgba(59,130,246,.12)", fg: "#1d4ed8", br: "rgba(59,130,246,.20)" },
      violet:{ bg:"rgba(124,58,237,.14)", fg:"#5b21b6", br:"rgba(124,58,237,.25)" },

      cyan: { bg: "rgba(34,211,238,.14)", fg: "#155e75", br: "rgba(34,211,238,.28)" },
    };

    const c = map[tone] ?? map.slate;
    return {
      display: "inline-flex",
      alignItems: "center",
      padding: "6px 10px",
      borderRadius: 999,
      background: c.bg,
      color: c.fg,
      border: `1px solid ${c.br}`,
      fontSize: 12,
      fontWeight: 800,
      lineHeight: 1,
      whiteSpace: "nowrap",
    };
  },

  err: {
    padding: "10px 12px",
    borderRadius: 14,
    background: "rgba(220, 38, 38, .10)",
    border: "1px solid rgba(220, 38, 38, .30)",
    color: "#991b1b",
    fontWeight: 700,
    marginTop: 10,
  },

  formGrid: { display: "grid", gridTemplateColumns: "1fr 1fr", gap: 10, marginTop: 10 },
  input: {
    height: 36,
    borderRadius: 12,
    border: "1px solid rgba(15,23,42,.12)",
    padding: "0 12px",
    outline: "none",
    background: "#fff",
    width: "100%",
  },
  inputWide: {
    height: 36,
    borderRadius: 12,
    border: "1px solid rgba(15,23,42,.12)",
    padding: "0 12px",
    outline: "none",
    background: "#fff",
    width: "100%",
  },
  actions: { display: "flex", gap: 10, marginTop: 12, flexWrap: "wrap" },
  accept: {
    padding: "10px 14px",
    borderRadius: 14,
    border: "1px solid rgba(34,197,94,.30)",
    background: "linear-gradient(135deg, rgba(34,197,94,.18), rgba(34,197,94,.10))",
    color: "#166534",
    fontWeight: 900,
    cursor: "pointer",
  },
  reject: {
    padding: "10px 14px",
    borderRadius: 14,
    border: "1px solid rgba(239,68,68,.30)",
    background: "linear-gradient(135deg, rgba(239,68,68,.16), rgba(239,68,68,.08))",
    color: "#991b1b",
    fontWeight: 900,
    cursor: "pointer",
  },

  ddWrap: { position: "relative" },
  ddBtn: {
    height: 32,
    width: "100%",
    borderRadius: 10,
    border: "1px solid rgba(15,23,42,.12)",
    padding: "0 10px",
    background: "#fff",
    color: "#0f172a",
    display: "flex",
    alignItems: "center",
    justifyContent: "space-between",
    gap: 8,
    cursor: "pointer",
    fontWeight: 800,
    fontSize: 13,
  },

  ddMenu: {
    position: "absolute",
    top: 38,
    left: 0,
    right: 0,
    background: "#fff",
    border: "1px solid rgba(15,23,42,.12)",
    borderRadius: 12,
    boxShadow: "0 18px 45px rgba(15,23,42,.16)",
    overflow: "hidden",
    zIndex: 50,
    maxHeight: 240,
    overflowY: "auto",
  },

  ddGroup: {
    padding: "6px 10px",
    fontSize: 10,
    fontWeight: 900,
    color: "#475569",
    background: "#f8fafc",
    borderBottom: "1px solid rgba(15,23,42,.06)",
    position: "sticky",
    top: 0,
    zIndex: 1,
  },

  ddItem: {
    padding: "8px 10px",
    display: "flex",
    alignItems: "center",
    justifyContent: "space-between",
    gap: 10,
    cursor: "pointer",
    fontWeight: 800,
    fontSize: 13,
    color: "#0f172a",
    borderBottom: "1px solid rgba(15,23,42,.06)",
  },

  ddItemHover: { background: "rgba(15,23,42,.03)" },
  ddRight: { display: "flex", alignItems: "center", gap: 8, flexShrink: 0 },
};