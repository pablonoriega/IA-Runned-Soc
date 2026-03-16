import React, { useEffect, useState } from "react";
import { fetchTrainingSession } from "../../services/api";

export default function TrainingResultPage({ sessionId, onBackHome, onRestart }) {
  const [data, setData] = useState(null);
  const [err, setErr] = useState("");
  const [loading, setLoading] = useState(false);

  async function load() {
    setLoading(true);
    setErr("");
    try {
      const r = await fetchTrainingSession(sessionId);
      setData(r);
    } catch (e) {
      setErr(String(e?.message ?? e));
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    load();
  }, [sessionId]);

  const card = {
    padding: 16,
    borderRadius: 16,
    border: "1px solid rgba(15,23,42,.12)",
    background: "#f1f5f9",
    boxShadow: "0 2px 10px rgba(15,23,42,.06)",
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

  if (loading) return <div style={{ padding: 20 }}>Cargando resultados…</div>;
  if (err) return <div style={{ padding: 20, color: "#991b1b", fontWeight: 900 }}>{err}</div>;
  if (!data?.session) return <div style={{ padding: 20 }}>No encontrado.</div>;

  const s = data.session;
  const answers = data.answers ?? [];

  return (
    <div style={{ padding: 20 }}>
      <div style={card}>
        <h2 style={{ margin: 0, fontSize: 24, fontWeight: 1100, color: "#0f172a" }}>
          Resultado · Sesión #{s.session_id}
        </h2>

        <div style={{ marginTop: 10, display: "flex", gap: 10, flexWrap: "wrap", color: "#475569", fontWeight: 900 }}>
          <div>Estado: {s.status}</div>
          <div>Aciertos: {s.correct_count}</div>
          <div>Fallos: {s.wrong_count}</div>
          <div>Score: {Number(s.score_pct ?? 0).toFixed(1)}%</div>
        </div>

        <div style={{ marginTop: 12, display: "flex", gap: 10, flexWrap: "wrap" }}>
          <button style={ghostBtn} onClick={onBackHome}>Volver al histórico</button>
          <button style={ghostBtn} onClick={onRestart}>Nuevo entrenamiento</button>
          <button style={ghostBtn} onClick={load}>Actualizar</button>
        </div>
      </div>

      <div style={{ marginTop: 14 }}>
        <div style={{ fontWeight: 1000, color: "#0f172a" }}>Detalle</div>

        {answers.length === 0 ? (
          <div style={{ marginTop: 8, color: "#64748b", fontWeight: 800 }}>No hay respuestas guardadas.</div>
        ) : (
          <table style={table}>
            <thead>
              <tr>
                <th style={th}>#</th>
                <th style={th}>Hora</th>
                <th style={th}>Tu acción</th>
                <th style={th}>Correcta</th>
                <th style={th}>OK</th>
                <th style={th}>Feedback</th>
              </tr>
            </thead>
            <tbody>
              {answers.map((a, idx) => (
                <tr key={a.answer_id}>
                  <td style={td}>{idx + 1}</td>
                  <td style={td}>{a.answered_at}</td>
                  <td style={td}>{a.operator_action}</td>
                  <td style={td}>{a.correct_action}</td>
                  <td style={td}>

                    <span style={{ fontWeight: 1000, color: a.is_correct ? "#166534" : "#991b1b" }}>
                      {a.is_correct ? "✅" : "❌"}
                    </span>
                  </td>
                  <td style={td}>{a.feedback_text}</td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </div>
    </div>
  );
}