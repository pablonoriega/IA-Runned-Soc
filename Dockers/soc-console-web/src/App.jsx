import React, { useEffect, useMemo, useState } from "react";
import QueuePage from "./pages/QueuePage.jsx";
import AlertDetailPage from "./pages/AlertDetailPage.jsx";
import SocStatusPage from "./pages/SocStatusPage.jsx";
import HistoryPage from "./pages/HistoryPage.jsx";
import TrainingPage from "./pages/TrainingPage.jsx";
import MlModelsPage from "./pages/MlModelsPage.jsx";
import { fetchSocMetrics } from "./services/api";

function fmtHMS(sec) {
  const s = Number(sec);
  if (!Number.isFinite(s) || s < 0) return "-";

  const total = Math.round(s);

  const h = Math.floor(total / 3600);
  const m = Math.floor((total % 3600) / 60);
  const r = total % 60;

  if (h > 0) return `${h}h ${String(m).padStart(2, "0")}m ${String(r).padStart(2, "0")}s`;
  if (m > 0) return `${m}m ${String(r).padStart(2, "0")}s`;
  return `${r}s`;
}

function MetricCard({ title, value, subtitle, loading, err }) {
  const card = {
    minWidth: 190,
    padding: "10px 12px",
    borderRadius: 14,
    border: "1px solid rgba(15,23,42,.12)",
    background: "#ffffff",
    boxShadow: "0 2px 8px rgba(15,23,42,.08)",
  };

  const k = { fontSize: 11, fontWeight: 900, color: "#475569", textTransform: "uppercase", letterSpacing: 0.4 };
  const v = { marginTop: 6, fontSize: 18, fontWeight: 1000, color: "#0f172a", lineHeight: 1.1 };
  const sub = { marginTop: 6, fontSize: 12, fontWeight: 800, color: "#64748b" };
  const errS = { marginTop: 6, fontSize: 12, fontWeight: 900, color: "#991b1b" };

  return (
    <div style={card}>
      <div style={k}>{title}</div>
      <div style={v}>{loading ? "…" : err ? "-" : value}</div>
      {err ? <div style={errS}>{String(err)}</div> : <div style={sub}>{subtitle}</div>}
    </div>
  );
}

export default function App() {
  const [selectedId, setSelectedId] = useState(null);
  const [view, setView] = useState("queue"); // queue | status | history | training | detail

  // métricas SOC
  const [mLoading, setMLoading] = useState(false);
  const [mErr, setMErr] = useState("");
  const [metrics, setMetrics] = useState(null);

  const openDetail = (alertId) => {
    setSelectedId(alertId);
    setView("detail");
  };

  const goQueue = () => {
    setSelectedId(null);
    setView("queue");
  };

  const goStatus = () => {
    setSelectedId(null);
    setView("status");
  };

  const goHistory = () => {
    setSelectedId(null);
    setView("history");
  };

  const goTraining = () => {
    setSelectedId(null);
    setView("training");
  };

  const backFromDetail = () => {
    setView("queue");
  };

  const tabBtn = (active) => ({
    padding: "10px 16px",
    borderRadius: 14,
    border: active ? "1px solid rgba(124,58,237,.55)" : "1px solid rgba(15,23,42,.12)",
    background: active ? "linear-gradient(135deg,#0b1220 0%, #4c1d95 100%)" : "#ffffff",
    color: active ? "#ffffff" : "#0f172a",
    cursor: "pointer",
    fontWeight: 900,
    boxShadow: active ? "0 8px 22px rgba(124,58,237,.35)" : "0 2px 8px rgba(15,23,42,.08)",
    transition: "all .15s ease",
  });

  useEffect(() => {
    let alive = true;

    (async () => {
      setMLoading(true);
      setMErr("");
      try {
        const data = await fetchSocMetrics({ days: 7 });
        if (!alive) return;
        setMetrics(data);
      } catch (e) {
        if (!alive) return;
        setMErr(String(e));
        setMetrics(null);
      } finally {
        if (!alive) return;
        setMLoading(false);
      }
    })();

    return () => {
      alive = false;
    };
  }, [view]);

  const resolveAvg = useMemo(() => metrics?.resolve?.avg_seconds, [metrics]);
  const ackAvg = useMemo(() => metrics?.ack?.avg_seconds, [metrics]);
  const resolveN = useMemo(() => metrics?.resolve?.considered ?? 0, [metrics]);
  const ackN = useMemo(() => metrics?.ack?.considered ?? 0, [metrics]);

  return (
    <div className="soc-shell">
      <div
        className="soc-header"
        style={{
          display: "flex",
          alignItems: "flex-start",
          justifyContent: "space-between",
          gap: 14,
          flexWrap: "wrap",
        }}
      >
        {/* IZQ */}
        <div>
          <h1 className="soc-title">SOC CONSOLE</h1>
          <p className="soc-subtitle">Work queue + Estado del SOC</p>

          <div style={{ display: "flex", gap: 10, marginTop: 10, flexWrap: "wrap" }}>
            <button onClick={goQueue} style={tabBtn(view === "queue")}>Work Queue</button>
            <button onClick={goStatus} style={tabBtn(view === "status")}>Estado SOC</button>
            <button onClick={goHistory} style={tabBtn(view === "history")}>Historico</button>
            <button onClick={() => { setSelectedId(null); setView("training"); }} style={tabBtn(view === "training")}>
              Entrenamiento
            </button>
            <button onClick={() => { setSelectedId(null); setView("mlmodels"); }} style={tabBtn(view === "mlmodels")}>
              Modelo de predicción
            </button>          
          </div>
        </div>

        {/* DER métricas */}
        <div style={{ display: "flex", gap: 10, flexWrap: "wrap", justifyContent: "flex-end" }}>
          <MetricCard
            title="Avg resolve SLA"
            value={fmtHMS(resolveAvg)}
            subtitle={`Últimos 7 días · n=${resolveN}`}
            loading={mLoading}
            err={mErr}
          />
          <MetricCard
            title="Avg ACK SLA"
            value={fmtHMS(ackAvg)}
            subtitle={`Últimos 7 días · n=${ackN}`}
            loading={mLoading}
            err={mErr}
          />
        </div>
      </div>

      <div className="soc-grid detail">
        <div className="soc-card">
          <div className="soc-card-inner">
            {view === "queue" && <QueuePage onSelect={openDetail} selectedId={selectedId} />}
            {view === "status" && <SocStatusPage onBack={goQueue} onSelect={openDetail} />}
            {view === "history" && <HistoryPage onSelect={openDetail} />}
            {view === "training" && <TrainingPage />}
            {view === "detail" && <AlertDetailPage alertId={selectedId} onBack={backFromDetail} />}
            {view === "mlmodels" && <MlModelsPage />}
          </div>
        </div>
      </div>
    </div>
  );
}