import React, { useEffect, useMemo, useState } from "react";
import { fetchTrainingNext, submitTrainingAnswer, finishTrainingSession } from "../../services/api";

const ACTIONS = [
  "ignore",
  "investigate",
  "block_ip",
  "reset_credentials",
  "disable_account",
  "isolate_host",
  "escalate_incident",
];

function FieldRow({ k, v }) {
  return (
    <div
      style={{
        display: "grid",
        gridTemplateColumns: "220px 1fr",
        gap: 10,
        padding: "8px 0",
        borderTop: "1px solid #e2e8f0",
      }}
    >
      <div style={{ fontWeight: 900, color: "#475569", fontSize: 12 }}>{k}</div>
      <div style={{ fontWeight: 900, color: "#0f172a", fontSize: 13, wordBreak: "break-word" }}>
        {String(v ?? "-")}
      </div>
    </div>
  );
}

export default function TrainingRunPage({ sessionId, onFinish }) {
  const [item, setItem] = useState(null); // { item_id, alert_payload }
  const [loading, setLoading] = useState(false);
  const [err, setErr] = useState("");

  const [action, setAction] = useState("investigate");
  const [reason, setReason] = useState("");

  const [grade, setGrade] = useState(null);
  const [progress, setProgress] = useState(null);
  const [submitting, setSubmitting] = useState(false);

  const alertPayload = useMemo(() => item?.alert_payload || null, [item]);

  async function loadNext() {
    setLoading(true);
    setErr("");
    setGrade(null);
    try {
      const data = await fetchTrainingNext(sessionId);
      if (!data?.item_id) {
        // no hay más: terminar
        await finishTrainingSession(sessionId);
        onFinish?.();
        return;
      }
      setItem({ item_id: data.item_id, alert_payload: data.alert_payload });
      setReason("");
      setAction("investigate");
    } catch (e) {
      setErr(String(e?.message ?? e));
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    loadNext();
  }, [sessionId]);

  const wrap = {
    padding: 16,
    borderRadius: 16,
    border: "1px solid rgba(15,23,42,.12)",
    background: "#f1f5f9",
    boxShadow: "0 2px 10px rgba(15,23,42,.06)",
  };

  const panel = {
    padding: 14,
    borderRadius: 16,
    border: "1px solid rgba(15,23,42,.12)",
    background: "#f8fafc",
    boxShadow: "0 2px 10px rgba(15,23,42,.06)",
    marginTop: 14,
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

  const input = {
    width: "100%",
    padding: "10px 12px",
    borderRadius: 12,
    border: "1px solid rgba(15,23,42,.12)",
    fontWeight: 900,
    outline: "none",
    background: "#fff",
    color: "#000",
  };

  if (loading) return <div style={{ padding: 20 }}>Cargando entrenamiento…</div>;
  if (err) return <div style={{ padding: 20, color: "#991b1b", fontWeight: 900 }}>{err}</div>;
  if (!item) return <div style={{ padding: 20 }}>Sin preguntas.</div>;

  return (
    <div style={{ padding: 20 }}>
      <div style={wrap}>
        <h2 style={{ margin: 0, fontSize: 22, fontWeight: 1100, color: "#0f172a" }}>
          Entrenamiento · Sesión #{sessionId} · Pregunta #{item.item_id}
        </h2>
        {progress ? (
          <div style={{ marginTop: 8, color: "#475569", fontWeight: 900, fontSize: 12 }}>
            Progreso: respondidas {progress.answered} · aciertos {progress.correct} · fallos {progress.wrong} · score{" "}
            {Number(progress.score_pct ?? 0).toFixed(1)}%
          </div>
        ) : null}
      </div>

      <div style={panel}>
        <div style={{ fontWeight: 1000, color: "#0f172a" }}>Datos de la alerta (simulada)</div>

        {!alertPayload ? (
          <div style={{ marginTop: 8, color: "#64748b", fontWeight: 800 }}>No payload</div>
        ) : (
          <div
            style={{
              marginTop: 10,
              background: "#fff",
              borderRadius: 12,
              border: "1px solid rgba(15,23,42,.10)",
              padding: 12,
            }}
          >
            {Object.entries(alertPayload).map(([k, v]) => (
              <FieldRow key={k} k={k} v={v} />
            ))}
          </div>
        )}
      </div>

      <div style={panel}>
        <div style={{ fontWeight: 1000, color: "#0f172a" }}>Tu decisión</div>

        <div style={{ marginTop: 10, display: "grid", gap: 10 }}>
          <div>
            <div style={{ fontSize: 12, fontWeight: 900, color: "#475569", marginBottom: 6 }}>Acción</div>
            <select style={input} value={action} onChange={(e) => setAction(e.target.value)}>
              {ACTIONS.map((a) => (
                <option key={a} value={a}>
                  {a}
                </option>
              ))}
            </select>
          </div>

          <div>
            <div style={{ fontSize: 12, fontWeight: 900, color: "#475569", marginBottom: 6 }}>Justificación</div>
            <textarea
              style={{ ...input, minHeight: 110, resize: "vertical" }}
              value={reason}
              onChange={(e) => setReason(e.target.value)}
              placeholder="Explica por qué eliges esta acción…"
            />
          </div>

          <div style={{ display: "flex", gap: 10, justifyContent: "flex-end", flexWrap: "wrap" }}>
            <button
              style={ghostBtn}
              onClick={async () => {
                await finishTrainingSession(sessionId);
                onFinish?.();
              }}
            >
              Finalizar ahora
            </button>

            <button
              style={btn}
              disabled={submitting || !reason.trim()}
              onClick={async () => {
                if (!reason.trim() || submitting) return;
                setSubmitting(true);
                try {
                  const r = await submitTrainingAnswer(sessionId, {
                    item_id: item.item_id,
                    operator_action: action,
                    operator_reason: reason,
                  });
                  setGrade(r.grade);
                  setProgress(r.progress);
                } catch (e) {
                  window.alert(String(e?.message ?? e));
                } finally {
                  setSubmitting(false);
                }
              }}
            >
              {submitting ? "Corrigiendo…" : "Enviar respuesta"}
            </button>
          </div>
        </div>
      </div>

      {grade ? (
        <div style={panel}>
          <div style={{ fontWeight: 1100, color: grade.is_correct ? "#166534" : "#991b1b" }}>
            {grade.is_correct ? "✅ Correcto" : "❌ Incorrecto"}
          </div>
          <div style={{ marginTop: 8, fontWeight: 900, color: "#0f172a" }}>
            Acción correcta: <span style={{ color: "#475569" }}>{grade.correct_action}</span>
          </div>
          <div style={{ marginTop: 8, color: "#475569", fontWeight: 850, whiteSpace: "pre-wrap" }}>
            {grade.feedback_text}
          </div>

          <div style={{ display: "flex", justifyContent: "flex-end", marginTop: 12 }}>
            <button style={btn} onClick={loadNext}>
              Siguiente
            </button>
          </div>
        </div>
      ) : null}
    </div>
  );
}