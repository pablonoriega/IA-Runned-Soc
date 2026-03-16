import React, { useEffect, useState } from "react";
import { fetchTrainingSessions } from "../../services/api";

export default function TrainingHomePage({ onStart, onOpenResult }) {
  const [items, setItems] = useState([]);
  const [loading, setLoading] = useState(false);
  const [err, setErr] = useState("");

  async function load() {
    setLoading(true);
    setErr("");
    try {
      const data = await fetchTrainingSessions();
      setItems(data?.items ?? []);
    } catch (e) {
      setErr(String(e?.message ?? e));
      setItems([]);
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    load();
  }, []);

  const card = {
    padding: 16,
    borderRadius: 16,
    border: "1px solid rgba(15,23,42,.12)",
    background: "#f1f5f9",
    boxShadow: "0 2px 10px rgba(15,23,42,.06)",
  };

  const btn = {
    padding: "10px 12px",
    borderRadius: 14,
    border: "1px solid rgba(124,58,237,.55)",
    background: "#0b1220",
    color: "#fff",
    cursor: "pointer",
    fontWeight: 900,
    boxShadow: "0 10px 28px rgba(15,23,42,.18)",
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

  const pill = {
    padding: "8px 10px",
    borderRadius: 999,
    border: "1px solid rgba(15,23,42,.12)",
    background: "#fff",
    color: "#0f172a",
    fontWeight: 900,
    fontSize: 12,
  };

  const table = {
    width: "100%",
    borderCollapse: "collapse",
    marginTop: 12,
    background: "#fff",
    border: "1px solid rgba(15,23,42,.10)",
    borderRadius: 12,
    overflow: "hidden",
  };

  const th = {
    textAlign: "left",
    padding: 10,
    background: "#f8fafc",
    fontSize: 12,
    fontWeight: 900,
    color: "#0f172a",
    borderBottom: "1px solid #e2e8f0",
  };

  const td = {
    padding: 10,
    borderTop: "1px solid #e2e8f0",
    fontSize: 13,
    color: "#0f172a",
    verticalAlign: "top",
  };

  return (
    <div style={{ padding: 20 }}>
      <div style={card}>
        <h2 style={{ margin: 0, fontSize: 26, fontWeight: 1100, color: "#0f172a" }}>Entrenamiento</h2>
        <div style={{ marginTop: 8, fontSize: 13, fontWeight: 850, color: "#475569" }}>
          Aquí verás tus entrenamientos anteriores (aciertos, fallos y puntuación). Pulsa “Comenzar entrenamiento” para iniciar uno nuevo.
        </div>

        <div style={{ display: "flex", gap: 10, flexWrap: "wrap", marginTop: 14, alignItems: "center" }}>
          <span style={pill}>Operador: soc_operator</span>

          <button style={ghostBtn} onClick={load}>
            {loading ? "Cargando…" : "Actualizar"}
          </button>

          <div style={{ marginLeft: "auto" }}>
            <button style={btn} onClick={onStart}>
              Comenzar entrenamiento
            </button>
          </div>
        </div>
      </div>

      {err ? <div style={{ padding: 12, color: "#991b1b", fontWeight: 900 }}>{err}</div> : null}

      <div style={{ marginTop: 14 }}>
        <div style={{ fontWeight: 1000, color: "#0f172a" }}>Histórico</div>

        {items.length === 0 ? (
          <div style={{ marginTop: 8, color: "#64748b", fontWeight: 800 }}>
            {loading ? "Cargando…" : "No hay entrenamientos todavía."}
          </div>
        ) : (
          <table style={table}>
            <thead>
              <tr>
                <th style={th}>Session</th>
                <th style={th}>Fecha</th>
                <th style={th}>Estado</th>
                <th style={th}>Aciertos</th>
                <th style={th}>Fallos</th>
                <th style={th}>Score</th>
                <th style={th}></th>
              </tr>
            </thead>
            <tbody>
              {items.map((s) => (
                <tr key={s.session_id}>
                  <td style={td}>#{s.session_id}</td>
                  <td style={td}>{s.created_at}</td>
                  <td style={td}>{s.status}</td>
                  <td style={td}>{s.correct_count}</td>
                  <td style={td}>{s.wrong_count}</td>
                  <td style={td}>{Number(s.score_pct ?? 0).toFixed(1)}%</td>
                  <td style={td}>
                    <button style={ghostBtn} onClick={() => onOpenResult?.(s.session_id)}>
                      Ver resultado
                    </button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </div>
    </div>
  );
}