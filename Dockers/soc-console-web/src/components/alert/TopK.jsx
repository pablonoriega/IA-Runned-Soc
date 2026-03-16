import React from "react";

export default function TopK({ topk }) {
  const items = Array.isArray(topk) ? topk : (topk?.top_k ?? []);
  if (!items || items.length === 0) return <div style={{ color: "#64748b" }}>Sin Top-K</div>;

  return (
    <div style={{ display: "grid", gap: 8 }}>
      {items.map((t, i) => (
        <div
          key={i}
          style={{
            display: "flex",
            alignItems: "center",
            justifyContent: "space-between",
            gap: 12,
            padding: "10px 12px",
            borderRadius: 14,
            border: "1px solid rgba(15,23,42,.10)",
            background:
              "linear-gradient(135deg, rgba(124,58,237,.10), rgba(59,130,246,.06))",
          }}
        >
          <div style={{ fontWeight: 900, color: "#0f172a" }}>{t.action}</div>
          <div
            style={{
              fontWeight: 900,
              padding: "6px 10px",
              borderRadius: 999,
              background: "rgba(15,23,42,.06)",
              border: "1px solid rgba(15,23,42,.10)",
              color: "#0f172a",
              fontSize: 12,
            }}
          >
            {(Number(t.prob) * 100).toFixed(1)}%
          </div>
        </div>
      ))}
    </div>
  );
}