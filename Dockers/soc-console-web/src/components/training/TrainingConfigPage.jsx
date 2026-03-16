import React, { useMemo, useState } from "react";
import { createTrainingSession } from "../../services/api";

const ATTACK_PHASES = ["reconnaissance", "initial_access", "execution", "lateral_movement", "exfiltration"];
const ALERT_TYPES = [
  "malware_detected",
  "ransomware_activity",
  "phishing_email",
  "credential_dump_detected",
  "suspicious_login",
  "brute_force_attempt",
  "port_scan",
  "command_and_control",
  "data_exfiltration",
  "privilege_escalation",
];
const ASSET_TYPES = ["workstation", "server", "database", "cloud_service"];
const SEVERITIES = [1, 2, 3, 4, 5];

function Pill({ active, label, onClick }) {
  return (
    <button
      type="button"
      onClick={onClick}
      style={{
        padding: "10px 12px",
        borderRadius: 999,
        border: active ? "1px solid rgba(124,58,237,.60)" : "1px solid rgba(15,23,42,.14)",
        background: active ? "rgba(124,58,237,.10)" : "#fff",
        color: "#0f172a",
        cursor: "pointer",
        fontWeight: 900,
        fontSize: 12,
        transition: "all .12s ease",
        boxShadow: active ? "0 6px 16px rgba(124,58,237,.16)" : "none",
      }}
    >
      {label}
    </button>
  );
}

function SectionCard({ title, subtitle, right, children }) {
  return (
    <div
      style={{
        marginTop: 14,
        padding: 14,
        borderRadius: 16,
        border: "1px solid rgba(15,23,42,.12)",
        background: "#f8fafc",
        boxShadow: "0 2px 10px rgba(15,23,42,.06)",
      }}
    >
      <div style={{ display: "flex", justifyContent: "space-between", gap: 10, flexWrap: "wrap" }}>
        <div>
          <div style={{ fontSize: 13, fontWeight: 1000, color: "#0f172a" }}>{title}</div>
          {subtitle ? (
            <div style={{ marginTop: 4, fontSize: 12, fontWeight: 800, color: "#64748b" }}>{subtitle}</div>
          ) : null}
        </div>
        {right}
      </div>
      <div style={{ marginTop: 12 }}>{children}</div>
    </div>
  );
}

export default function TrainingConfigPage({ onBack, onCreatedSession }) {
  const [operatorId] = useState(() => localStorage.getItem("soc_operator_id") || "unknown");

  const [phases, setPhases] = useState(new Set());
  const [types, setTypes] = useState(new Set());
  const [assets, setAssets] = useState(new Set());
  const [sevs, setSevs] = useState(new Set());
  const [total, setTotal] = useState(10);

  const [loading, setLoading] = useState(false);
  const [err, setErr] = useState("");

  const chipRow = { display: "flex", gap: 10, flexWrap: "wrap" };

  const toggleSet = (setter, value) => {
    setter((prev) => {
      const next = new Set(prev);
      next.has(value) ? next.delete(value) : next.add(value);
      return next;
    });
  };

  // seleccionar todo de una sección
  const selectAllInSection = (setter, values) => {
    setter(new Set(values));
  };

  const selectAll = () => {
    setPhases(new Set(ATTACK_PHASES));
    setTypes(new Set(ALERT_TYPES));
    setAssets(new Set(ASSET_TYPES));
    setSevs(new Set(SEVERITIES));
  };

  const clearAll = () => {
    setPhases(new Set());
    setTypes(new Set());
    setAssets(new Set());
    setSevs(new Set());
  };

  const valid = phases.size && types.size && assets.size && sevs.size;

  const config = useMemo(
    () => ({
      attack_phases: Array.from(phases),
      alert_types: Array.from(types),
      asset_types: Array.from(assets),
      severities: Array.from(sevs).sort((a, b) => a - b),
    }),
    [phases, types, assets, sevs]
  );

  const headerWrap = {
    padding: "16px 16px",
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
    cursor: valid && !loading ? "pointer" : "not-allowed",
    fontWeight: 900,
    boxShadow: "0 10px 28px rgba(15,23,42,.18)",
    opacity: valid && !loading ? 1 : 0.55,
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

  const counter = {
    padding: "6px 10px",
    borderRadius: 999,
    border: "1px solid rgba(15,23,42,.12)",
    background: "#fff",
    fontSize: 12,
    fontWeight: 900,
    color: "#0f172a",
  };

  const missingText = () => {
    const miss = [];
    if (!phases.size) miss.push("attack phase");
    if (!types.size) miss.push("tipos de alerta");
    if (!assets.size) miss.push("tipo de activo");
    if (!sevs.size) miss.push("severity");
    return miss.join(", ");
  };

  return (
    <div style={{ padding: 20 }}>
      <div style={headerWrap}>
        <h2 style={{ margin: 0, fontSize: 26, fontWeight: 1100, color: "#0f172a" }}>Bienvenido al modo entrenamiento</h2>
        <div style={{ marginTop: 8, fontSize: 13, fontWeight: 850, color: "#475569" }}>
          Seleccione la configuración con la que desee entrenar.
        </div>

        <div style={{ display: "flex", gap: 10, flexWrap: "wrap", marginTop: 14, alignItems: "center" }}>
          <button style={ghostBtn} onClick={onBack}>
            Volver
          </button>
          <button style={ghostBtn} onClick={selectAll}>
            Seleccionar todo
          </button>
          <button style={ghostBtn} onClick={clearAll}>
            Limpiar
          </button>

          <div style={{ marginLeft: "auto", display: "flex", gap: 8, flexWrap: "wrap" }}>
            <div style={counter}>
              Phases: {phases.size}/{ATTACK_PHASES.length}
            </div>
            <div style={counter}>
              Tipos: {types.size}/{ALERT_TYPES.length}
            </div>
            <div style={counter}>
              Activos: {assets.size}/{ASSET_TYPES.length}
            </div>
            <div style={counter}>
              Sev: {sevs.size}/{SEVERITIES.length}
            </div>
          </div>
        </div>

        <div style={{ marginTop: 12, display: "flex", gap: 10, flexWrap: "wrap", alignItems: "center" }}>
          <div style={{ fontWeight: 900, color: "#0f172a" }}>Preguntas:</div>
          {[10, 20, 50].map((n) => (
            <button key={n} style={ghostBtn} onClick={() => setTotal(n)}>
              {total === n ? `✓ ${n}` : n}
            </button>
          ))}
        </div>

        {!valid ? (
          <div style={{ marginTop: 10, fontSize: 12, fontWeight: 900, color: "#991b1b" }}>
            Falta seleccionar: {missingText()}
          </div>
        ) : null}

        {err ? <div style={{ marginTop: 10, fontSize: 12, fontWeight: 900, color: "#991b1b" }}>{err}</div> : null}
      </div>

      <SectionCard
        title="1) Attack phase"
        subtitle="Selecciona las fases del ataque."
        right={
          <div style={{ display: "flex", gap: 8, alignItems: "center" }}>
            <button style={ghostBtn} onClick={() => selectAllInSection(setPhases, ATTACK_PHASES)}>
              Seleccionar todas
            </button>
            <div style={counter}>{phases.size} seleccionadas</div>
          </div>
        }
      >
        <div style={chipRow}>
          {ATTACK_PHASES.map((p) => (
            <Pill key={p} label={p} active={phases.has(p)} onClick={() => toggleSet(setPhases, p)} />
          ))}
        </div>
      </SectionCard>

      <SectionCard
        title="2) Tipos de alerta"
        subtitle="Elige los tipos de alerta."
        right={
          <div style={{ display: "flex", gap: 8, alignItems: "center" }}>
            <button style={ghostBtn} onClick={() => selectAllInSection(setTypes, ALERT_TYPES)}>
              Seleccionar todas
            </button>
            <div style={counter}>{types.size} seleccionados</div>
          </div>
        }
      >
        <div style={chipRow}>
          {ALERT_TYPES.map((t) => (
            <Pill key={t} label={t} active={types.has(t)} onClick={() => toggleSet(setTypes, t)} />
          ))}
        </div>
      </SectionCard>

      <SectionCard
        title="3) Tipo de activo"
        subtitle="Selecciona activos."
        right={
          <div style={{ display: "flex", gap: 8, alignItems: "center" }}>
            <button style={ghostBtn} onClick={() => selectAllInSection(setAssets, ASSET_TYPES)}>
              Seleccionar todas
            </button>
            <div style={counter}>{assets.size} seleccionados</div>
          </div>
        }
      >
        <div style={chipRow}>
          {ASSET_TYPES.map((a) => (
            <Pill key={a} label={a} active={assets.has(a)} onClick={() => toggleSet(setAssets, a)} />
          ))}
        </div>
      </SectionCard>

      <SectionCard
        title="4) Severity"
        subtitle="Selecciona 1..5."
        right={
          <div style={{ display: "flex", gap: 8, alignItems: "center" }}>
            <button style={ghostBtn} onClick={() => selectAllInSection(setSevs, SEVERITIES)}>
              Seleccionar todas
            </button>
            <div style={counter}>{sevs.size} seleccionadas</div>
          </div>
        }
      >
        <div style={chipRow}>
          {SEVERITIES.map((s) => (
            <Pill key={s} label={`SEV ${s}`} active={sevs.has(s)} onClick={() => toggleSet(setSevs, s)} />
          ))}
        </div>
      </SectionCard>

      <div style={{ display: "flex", justifyContent: "flex-end", marginTop: 16 }}>
        <button
          style={btn}
          disabled={!valid || loading}
          onClick={async () => {
            if (!valid || loading) return;
            setLoading(true);
            setErr("");
            try {
              const s = await createTrainingSession({
                config,
                total_questions: total,
              });
              onCreatedSession?.(s.session_id);
            } catch (e) {
              setErr(String(e?.message ?? e));
            } finally {
              setLoading(false);
            }
          }}
        >
          {loading ? "Creando…" : "Comenzar entrenamiento"}
        </button>
      </div>
    </div>
  );
}