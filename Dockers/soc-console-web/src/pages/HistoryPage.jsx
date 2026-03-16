// src/pages/HistoricalPage.jsx
import React, { useEffect, useMemo, useState } from "react";
import { fetchAlerts, postRetrain  } from "../services/api";

function normDecision(x) {
  const v = String(x ?? "").trim().toUpperCase();
  if (!v) return "";
  if (v === "ACCEPT" || v === "ACCEPTED" || v === "APPROVE" || v === "APPROVED") return "ACCEPT";
  if (v === "REJECT" || v === "REJECTED" || v === "DENY" || v === "DENIED") return "REJECT";
  return v;
}

function Modal({ open, title, onClose, children }) {
  if (!open) return null;

  const overlay = {
    position: "fixed",
    inset: 0,
    background: "rgba(15,23,42,.45)",
    display: "flex",
    alignItems: "center",
    justifyContent: "center",
    padding: 16,
    zIndex: 9999,
  };

  const card = {
    width: "min(720px, 100%)",
    background: "#fff",
    borderRadius: 16,
    border: "1px solid rgba(15,23,42,.12)",
    boxShadow: "0 18px 60px rgba(2,6,23,.25)",
    overflow: "hidden",
  };

  const head = {
    padding: "12px 14px",
    borderBottom: "1px solid rgba(15,23,42,.10)",
    display: "flex",
    alignItems: "center",
    justifyContent: "space-between",
    gap: 10,
  };

  const closeBtn = {
    border: "1px solid rgba(15,23,42,.12)",
    background: "#fff",
    borderRadius: 12,
    padding: "8px 10px",
    cursor: "pointer",
    fontWeight: 900,
  };

  return (
    <div style={overlay} onMouseDown={onClose}>
      <div style={card} onMouseDown={(e) => e.stopPropagation()}>
        <div style={head}>
          <div style={{ fontWeight: 1000, color: "#0f172a" }}>{title}</div>
          <button style={closeBtn} onClick={onClose}>✕</button>
        </div>
        <div style={{ padding: 14 }}>{children}</div>
      </div>
    </div>
  );
}

// helpers para “chips” de scheduling
function pad2(n) {
  return String(n).padStart(2, "0");
}
function toDatetimeLocal(d) {
  const y = d.getFullYear();
  const mo = pad2(d.getMonth() + 1);
  const da = pad2(d.getDate());
  const h = pad2(d.getHours());
  const m = pad2(d.getMinutes());
  return `${y}-${mo}-${da}T${h}:${m}`;
}

export default function HistoricalPage({ onSelect, onSchedule }) {
  const [items, setItems] = useState([]);
  const [loading, setLoading] = useState(false);
  const [err, setErr] = useState("");

  // modal
  const [openSched, setOpenSched] = useState(false);

  // scheduling fields
  const [runNow, setRunNow] = useState(true);
  const [when, setWhen] = useState(""); // datetime-local
  const [onlyRejected, setOnlyRejected] = useState(true);

  useEffect(() => {
    (async () => {
      setLoading(true);
      setErr("");
      try {
        const data = await fetchAlerts({
          status: "CLOSED",
          limit: 500,
          offset: 0,
        });
        setItems(data?.items ?? []);
      } catch (e) {
        setErr(String(e));
        setItems([]);
      } finally {
        setLoading(false);
      }
    })();
  }, []);

  const accepted = useMemo(() => (items ?? []).filter((x) => normDecision(x?.human_decision) === "ACCEPT"), [items]);
  const rejected = useMemo(() => (items ?? []).filter((x) => normDecision(x?.human_decision) === "REJECT"), [items]);
  const other = useMemo(() => {
    return (items ?? []).filter((x) => {
      const d = normDecision(x?.human_decision);
      return d !== "ACCEPT" && d !== "REJECT";
    });
  }, [items]);

  const schedulePayload = () => ({
    type: "RETRAIN_MODEL",
    run_immediately: !!runNow,
    when: runNow ? null : (when || null),
    dataset: onlyRejected ? "rejected_only" : "all_closed",
  });

  // styles
  const table = {
    width: "100%",
    borderCollapse: "collapse",
    marginTop: 10,
    background: "#fff",
    border: "1px solid rgba(15,23,42,.10)",
    borderRadius: 12,
    overflow: "hidden",
  };

  const th = {
    textAlign: "left",
    padding: 10,
    background: "#f1f5f9",
    fontSize: 12,
    fontWeight: 900,
    color: "#0f172a",
    borderBottom: "1px solid #e2e8f0",
  };

  const td = {
    padding: 10,
    borderTop: "1px solid #e2e8f0",
    fontSize: 13,
    cursor: "pointer",
    color: "#0f172a",
    verticalAlign: "top",
  };

  const subtle = { color: "#64748b", fontWeight: 800 };

  const btn = {
    padding: "10px 12px",
    borderRadius: 14,
    border: "1px solid rgba(124,58,237,.55)",
    background: "linear-gradient(135deg,#0b1220 0%, #4c1d95 100%)",
    color: "#fff",
    cursor: "pointer",
    fontWeight: 900,
    boxShadow: "0 10px 28px rgba(124,58,237,.25)",
  };

  const ghostBtn = {
    padding: "10px 12px",
    borderRadius: 14,
    border: "1px solid rgba(15,23,42,.12)",
    background: "#fff",
    color: "#0f172a",
    cursor: "pointer",
    fontWeight: 900,
  };

  const input = {
    width: "100%",
    padding: "10px 12px",
    borderRadius: 12,
    border: "1px solid rgba(15,23,42,.12)",
    fontWeight: 900,
    outline: "none",
    background: "#fff",
  };

  const label = { fontSize: 12, fontWeight: 900, color: "#475569", marginBottom: 6 };

  const chipRow = { display: "flex", gap: 8, flexWrap: "wrap", marginTop: 8 };
  const chip = (active) => ({
    padding: "8px 10px",
    borderRadius: 999,
    border: active ? "1px solid rgba(124,58,237,.55)" : "1px solid rgba(15,23,42,.12)",
    background: active ? "rgba(124,58,237,.10)" : "#fff",
    color: "#0f172a",
    cursor: "pointer",
    fontWeight: 900,
    fontSize: 12,
  });

  const toggleWrap = {
    display: "flex",
    alignItems: "center",
    justifyContent: "space-between",
    gap: 10,
    padding: 12,
    borderRadius: 14,
    border: "1px solid rgba(15,23,42,.10)",
    background: "#f8fafc",
  };

  const section = (title, data, tone, headerRight) => (
    <div style={{ marginBottom: 28 }}>
      <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", gap: 10, flexWrap: "wrap" }}>
        <h3 style={{ marginBottom: 6 }}>
          {title} <span style={{ color: "#64748b", fontWeight: 900 }}>({data.length})</span>
        </h3>
        {headerRight}
      </div>

      {data.length === 0 ? (
        <div style={subtle}>No alerts</div>
      ) : (
        <table style={table}>
          <thead>
            <tr>
              <th style={th}>ID</th>
              <th style={th}>Type</th>
              <th style={th}>Phase</th>
              <th style={th}>Model action</th>
              <th style={th}>Decision</th>
              <th style={th}>Closed by</th>
              <th style={th}>Reason</th>
            </tr>
          </thead>
          <tbody>
            {data.map((a) => {
              const decision = normDecision(a.human_decision) || "-";
              return (
                <tr key={a.alert_id} onClick={() => onSelect?.(a.alert_id)}>
                  <td style={td}>#{a.alert_id}</td>
                  <td style={td}>{a.alert_type ?? "-"}</td>
                  <td style={td}>{a.attack_phase ?? "-"}</td>
                  <td style={td}>{a.model_recommended_action ?? "-"}</td>
                  <td style={{ ...td, fontWeight: 900, color: tone || "#0f172a" }}>{decision}</td>
                  <td style={td}>{a.human_decided_by ?? "-"}</td>
                  <td style={td}>{a.human_reason ?? "-"}</td>
                </tr>
              );
            })}
          </tbody>
        </table>
      )}
    </div>
  );

  if (loading) return <div style={{ padding: 20 }}>Loading historical…</div>;
  if (err) return <div style={{ padding: 20, color: "red" }}>{err}</div>;

  return (
    <div style={{ padding: 20 }}>
      <h2 style={{ marginBottom: 6 }}>Historical closed alerts</h2>
      <div style={{ color: "#64748b", fontWeight: 800, marginBottom: 14 }}>
        Click a row to open the alert detail.
      </div>

      {section("Accepted alerts", accepted, "#16a34a")}

      {section(
        "Rejected alerts (training set)",
        rejected,
        "#dc2626",
        <button style={btn} onClick={() => setOpenSched(true)}>
          Programar reentrenamiento
        </button>
      )}

      {section("Other / no decision", other, "#0f172a")}

      <Modal open={openSched} title="Programar reentrenamiento" onClose={() => setOpenSched(false)}>
        <div style={{ display: "grid", gap: 12 }}>
          {/* toggle “ahora” */}
          <div style={toggleWrap}>
            <div>
              <div style={{ fontWeight: 1000, color: "#0f172a" }}>Reentrenar inmediatamente</div>
              <div style={{ marginTop: 4, fontSize: 12, fontWeight: 800, color: "#64748b" }}>
                Si lo activas, se ejecuta ya (sin fecha/hora).
              </div>
            </div>

            <label style={{ display: "flex", alignItems: "center", gap: 10, fontWeight: 1000, color: "#0f172a" }}>
              <input
                type="checkbox"
                checked={runNow}
                onChange={(e) => setRunNow(e.target.checked)}
                style={{ width: 18, height: 18 }}
              />
              Ahora
            </label>
          </div>

          <div style={{ opacity: runNow ? 0.55 : 1 }}>
            <div style={label}>Fecha y hora</div>

            <div style={{ display: "grid", gridTemplateColumns: "1fr", gap: 8 }}>
              <input
                type="datetime-local"
                value={when}
                onChange={(e) => setWhen(e.target.value)}
                style={input}
                disabled={runNow}
              />
            </div>

            {/* chips rápidos */}
            <div style={chipRow}>
              <button
                type="button"
                style={chip(false)}
                disabled={runNow}
                onClick={() => {
                  const d = new Date();
                  d.setMinutes(d.getMinutes() + 15);
                  setWhen(toDatetimeLocal(d));
                }}
              >
                +15 min
              </button>

              <button
                type="button"
                style={chip(false)}
                disabled={runNow}
                onClick={() => {
                  const d = new Date();
                  d.setHours(d.getHours() + 1);
                  setWhen(toDatetimeLocal(d));
                }}
              >
                +1h
              </button>

              <button
                type="button"
                style={chip(false)}
                disabled={runNow}
                onClick={() => {
                  const d = new Date();
                  d.setDate(d.getDate() + 1);
                  d.setHours(9, 0, 0, 0);
                  setWhen(toDatetimeLocal(d));
                }}
              >
                Mañana 09:00
              </button>

              <button
                type="button"
                style={chip(false)}
                disabled={runNow}
                onClick={() => {
                  const d = new Date();
                  // próximo lunes 09:00
                  const day = d.getDay(); // 0 dom..6 sáb
                  const add = (8 - day) % 7 || 7;
                  d.setDate(d.getDate() + add);
                  d.setHours(9, 0, 0, 0);
                  setWhen(toDatetimeLocal(d));
                }}
              >
                Próx lunes 09:00
              </button>
            </div>

            {!runNow && !when ? (
              <div style={{ marginTop: 8, color: "#991b1b", fontWeight: 900, fontSize: 12 }}>
                Elige una fecha/hora o activa “Ahora”.
              </div>
            ) : null}
          </div>

          <div style={{ display: "grid", gridTemplateColumns: "1fr", gap: 12 }}>
            <div>
              <div style={label}>Dataset</div>
              <label style={{ display: "flex", alignItems: "center", gap: 8, fontWeight: 900, color: "#0f172a" }}>
                <input
                  type="checkbox"
                  checked={onlyRejected}
                  onChange={(e) => setOnlyRejected(e.target.checked)}
                />
                Solo rechazadas
              </label>
              <div style={{ marginTop: 6, color: "#64748b", fontWeight: 800, fontSize: 12 }}>
                {onlyRejected ? "Usa solo REJECT como set de reentreno." : "Usa todas las CLOSED."}
              </div>
            </div>
          </div>

          <div style={{ display: "flex", gap: 10, justifyContent: "flex-end", flexWrap: "wrap", marginTop: 6 }}>
            <button style={ghostBtn} onClick={() => setOpenSched(false)}>
              Cancelar
            </button>

            <button
            style={btn}
            onClick={async () => {
                if (!runNow && !when) return; // guard rail

                const payload = schedulePayload();

                try {
                await postRetrain(payload);         
                if (onSchedule) onSchedule(payload); 
                console.log("[retrain schedule]", payload);
                setOpenSched(false);
                } catch (e) {
                console.error("[retrain] error:", e);
                // si quieres, aquí puedes mostrar un toast o alert simple:
                alert(`Error programando reentreno: ${String(e?.message ?? e)}`);
                }
            }}
            >
            Programar
            </button>
          </div>

          <div style={{ marginTop: 8, fontSize: 12, color: "#64748b", fontWeight: 800 }}>
            Payload:
            <pre style={{ marginTop: 8, padding: 10, background: "#f8fafc", borderRadius: 12, overflow: "auto" }}>
              {JSON.stringify(schedulePayload(), null, 2)}
            </pre>
          </div>
        </div>
      </Modal>
    </div>
  );
}