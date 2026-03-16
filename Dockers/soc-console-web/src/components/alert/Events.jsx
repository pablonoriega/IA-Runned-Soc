import React from "react";
import EmptyState from "../common/EmptyState";

export default function Events({ events }) {
  if (!events) return null;

  if (events.length === 0) {
    return (
      <EmptyState
        title="Sin eventos"
        description="No hay eventos disponibles para esta alerta."
        tone="slate"
      />
    );
  }

  return (
    <div style={{ marginTop: 12 }}>
      <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", gap: 10 }}>
        <h3 style={{ margin: 0 }}>Timeline</h3>
        <span style={{ fontSize: 12, fontWeight: 800, color: "#64748b" }}>
          {events.length} {events.length === 1 ? "evento" : "eventos"}
        </span>
      </div>

      <ul style={{ paddingLeft: 18, marginTop: 10, marginBottom: 0 }}>
        {events.map((ev) => (
          <li key={ev.event_id} style={{ marginBottom: 8, color: "#0f172a" }}>
            <div style={{ fontWeight: 900 }}>
              {ev.event_type ?? "-"}
              <span style={{ fontWeight: 800, color: "#64748b" }}> — {ev.actor ?? "-"}</span>
            </div>
            <div style={{ marginTop: 2, fontSize: 12, fontWeight: 800, color: "#64748b" }}>
              {ev.event_time ?? "-"}
            </div>
          </li>
        ))}
      </ul>
    </div>
  );
}