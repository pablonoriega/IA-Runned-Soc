import React from "react";
import Badge from "./Badge";

export default function EmptyState({
  title = "No data",
  description = "",
  tone = "slate",
  actions = null,
  style,
}) {
  return (
    <div
      style={{
        padding: 14,
        borderRadius: 16,
        border: "1px dashed rgba(15,23,42,.18)",
        background: "rgba(248,250,252,.8)",
        color: "#0f172a",
        ...style,
      }}
    >
      <div style={{ display: "flex", alignItems: "center", gap: 10, marginBottom: 8 }}>
        <Badge tone={tone}>{title}</Badge>
      </div>

      {description ? (
        <div style={{ color: "#64748b", fontWeight: 700, fontSize: 13, lineHeight: 1.35 }}>
          {description}
        </div>
      ) : null}

      {actions ? <div style={{ marginTop: 12 }}>{actions}</div> : null}
    </div>
  );
}