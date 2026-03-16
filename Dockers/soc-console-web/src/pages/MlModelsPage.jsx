import React, { useEffect, useMemo, useState } from "react";
import { fetchMlModels, fetchMlModelDetail } from "../services/api";

function Badge({ children, tone = "neutral" }) {
  const tones =
    {
      neutral: { bg: "rgba(15,23,42,.06)", fg: "#0f172a", bd: "rgba(15,23,42,.12)" },
      success: { bg: "rgba(16,185,129,.12)", fg: "#065f46", bd: "rgba(16,185,129,.25)" },
      danger: { bg: "rgba(239,68,68,.12)", fg: "#7f1d1d", bd: "rgba(239,68,68,.25)" },
      purple: { bg: "rgba(124,58,237,.12)", fg: "#4c1d95", bd: "rgba(124,58,237,.25)" },
    }[tone] || { bg: "rgba(15,23,42,.06)", fg: "#0f172a", bd: "rgba(15,23,42,.12)" };

  return (
    <span
      style={{
        display: "inline-flex",
        alignItems: "center",
        gap: 6,
        padding: "6px 10px",
        borderRadius: 999,
        border: `1px solid ${tones.bd}`,
        background: tones.bg,
        color: tones.fg,
        fontWeight: 900,
        fontSize: 12,
      }}
    >
      {children}
    </span>
  );
}

function Card({ title, value, subtitle }) {
  return (
    <div
      style={{
        padding: "12px 14px",
        borderRadius: 16,
        border: "1px solid rgba(15,23,42,.12)",
        background: "#fff",
        boxShadow: "0 2px 10px rgba(15,23,42,.08)",
        minWidth: 210,
      }}
    >
      <div style={{ fontSize: 11, fontWeight: 1000, color: "#475569", textTransform: "uppercase", letterSpacing: 0.5 }}>
        {title}
      </div>
      <div style={{ marginTop: 6, fontSize: 22, fontWeight: 1100, color: "#0f172a", lineHeight: 1.1 }}>
        {value ?? "—"}
      </div>
      <div style={{ marginTop: 6, fontSize: 12, fontWeight: 800, color: "#64748b" }}>
        {subtitle ?? ""}
      </div>
    </div>
  );
}

function fmtPct(x) {
  const n = Number(x);
  if (!Number.isFinite(n)) return "—";
  return `${(n * 100).toFixed(1)}%`;
}

function fmtNum(x, digits = 3) {
  const n = Number(x);
  if (!Number.isFinite(n)) return "—";
  return n.toFixed(digits);
}

function ConfusionMatrix({ matrix, labels }) {
  if (!Array.isArray(matrix) || matrix.length === 0) return null;

  const n = matrix.length;

  // Si no llegan labels o no cuadran, generamos fallback
  const labs =
    Array.isArray(labels) && labels.length === n
      ? labels
      : Array.from({ length: n }, (_, i) => `C${i}`);

  const headerCell = {
    padding: "10px 10px",
    fontSize: 12,
    fontWeight: 1000,
    color: "#475569",
    textTransform: "uppercase",
    letterSpacing: 0.5,
    whiteSpace: "nowrap",
  };

  const labelChip = (text) => (
    <span
      title={text}
      style={{
        display: "inline-flex",
        maxWidth: 170,
        overflow: "hidden",
        textOverflow: "ellipsis",
        whiteSpace: "nowrap",
        fontWeight: 1100,
        color: "#0f172a",
        textTransform: "none",
      }}
    >
      {text}
    </span>
  );

  return (
    <div style={{ overflowX: "auto" }}>
      {/* Guía Real/Pred */}
      <div style={{ marginBottom: 8, fontSize: 12, fontWeight: 1000, color: "#475569" }}>
        <span style={{ fontWeight: 1100, color: "#0f172a" }}>Real</span> ↓ &nbsp;·&nbsp;
        <span style={{ fontWeight: 1100, color: "#0f172a" }}>Predicción</span> →
      </div>

      <table style={{ borderCollapse: "separate", borderSpacing: 10 }}>
        <thead>
          <tr>
            <th style={headerCell}></th>
            <th style={{ ...headerCell, textAlign: "center" }} colSpan={n}>
              Predicción →
            </th>
          </tr>
          <tr>
            <th style={headerCell}></th>
            {labs.map((lab) => (
              <th key={lab} style={{ ...headerCell, textAlign: "center" }} title={lab}>
                {labelChip(lab)}
              </th>
            ))}
          </tr>
        </thead>

        <tbody>
          {matrix.map((row, i) => (
            <tr key={i}>
              {/* header fila = REAL */}
              <th style={{ ...headerCell, textAlign: "right" }} title={labs[i]}>
                {labelChip(labs[i])}
              </th>

              {row.map((cell, j) => {
                const v = Number(cell);
                const intensity = Number.isFinite(v) ? Math.min(1, Math.log10(v + 1) / 3) : 0;
                const bg = `rgba(124,58,237,${0.10 + intensity * 0.25})`;

                // destacar diagonal (aciertos)
                const isDiag = i === j;

                return (
                  <td
                    key={j}
                    style={{
                      padding: "14px 12px",
                      borderRadius: 14,
                      border: isDiag ? "1px solid rgba(124,58,237,.55)" : "1px solid rgba(15,23,42,.12)",
                      background: bg,
                      textAlign: "center",
                      fontWeight: 1100,
                      color: "#0f172a",
                      minWidth: 90,
                      boxShadow: isDiag ? "0 6px 14px rgba(124,58,237,.18)" : "none",
                    }}
                    title={`Real=${labs[i]} · Pred=${labs[j]}`}
                  >
                    {Number.isFinite(v) ? v : "—"}
                  </td>
                );
              })}
            </tr>
          ))}
        </tbody>
      </table>

      <div style={{ marginTop: 6, fontSize: 12, fontWeight: 800, color: "#64748b" }}>
        Filas = clase real · Columnas = clase predicha
      </div>
    </div>
  );
}

function SimpleTable({ columns, rows }) {
  return (
    <div style={{ overflowX: "auto" }}>
      <table style={{ width: "100%", borderCollapse: "separate", borderSpacing: 0 }}>
        <thead>
          <tr>
            {columns.map((c) => (
              <th
                key={c.key}
                style={{
                  textAlign: c.align || "left",
                  padding: "10px 10px",
                  fontSize: 12,
                  fontWeight: 1000,
                  color: "#475569",
                  borderBottom: "1px solid rgba(15,23,42,.10)",
                  whiteSpace: "nowrap",
                }}
              >
                {c.label}
              </th>
            ))}
          </tr>
        </thead>
        <tbody>
          {rows.map((r, idx) => (
            <tr key={idx}>
              {columns.map((c) => (
                <td
                  key={c.key}
                  style={{
                    padding: "10px 10px",
                    borderBottom: "1px solid rgba(15,23,42,.08)",
                    fontSize: 13,
                    fontWeight: 800,
                    color: "#0f172a",
                    textAlign: c.align || "left",
                    whiteSpace: "nowrap",
                  }}
                >
                  {r[c.key]}
                </td>
              ))}
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

export default function MlModelsPage() {
  const [loadingList, setLoadingList] = useState(false);
  const [listErr, setListErr] = useState("");
  const [models, setModels] = useState([]);
  const [activeVersion, setActiveVersion] = useState(null);

  const [selected, setSelected] = useState(null);

  const [loadingDetail, setLoadingDetail] = useState(false);
  const [detailErr, setDetailErr] = useState("");
  const [detail, setDetail] = useState(null);

  // 1) cargar lista
  useEffect(() => {
    let alive = true;
    (async () => {
      setLoadingList(true);
      setListErr("");
      try {
        const data = await fetchMlModels();
        if (!alive) return;
        setModels(data?.models ?? []);
        setActiveVersion(data?.active_version ?? null);

        // auto-select activo o primero
        const v = data?.active_version ?? (data?.models?.[0]?.version ?? null);
        setSelected(v);
      } catch (e) {
        if (!alive) return;
        setListErr(String(e));
      } finally {
        if (!alive) return;
        setLoadingList(false);
      }
    })();
    return () => {
      alive = false;
    };
  }, []);

  // 2) cargar detalle cuando cambia selección
  useEffect(() => {
    if (!selected) return;
    let alive = true;

    (async () => {
      setLoadingDetail(true);
      setDetailErr("");
      try {
        const data = await fetchMlModelDetail(selected);
        if (!alive) return;
        setDetail(data);
      } catch (e) {
        if (!alive) return;
        setDetailErr(String(e));
        setDetail(null);
      } finally {
        if (!alive) return;
        setLoadingDetail(false);
      }
    })();

    return () => {
      alive = false;
    };
  }, [selected]);

  const modelMeta = detail?.model ?? null;
  const latestMetrics = detail?.latest_metrics ?? null;
  const confusion = latestMetrics?.confusion ?? null;
  const metricsObj = latestMetrics?.metrics ?? null;

  const importancePermutation = detail?.importances?.PERMUTATION ?? null;
  const importanceShap = detail?.importances?.SHAP ?? null;

  const cards = useMemo(() => {
    const acc = metricsObj?.accuracy;
    const macroF1 = metricsObj?.macro_avg?.["f1-score"];
    const weightedF1 = metricsObj?.weighted_avg?.["f1-score"];
    const nInfo = metricsObj?.train_info;

    return [
      {
        title: "Accuracy",
        value: Number.isFinite(Number(acc)) ? fmtPct(acc) : "—",
        subtitle: "Evaluación (split test)",
      },
      {
        title: "F1 macro",
        value: Number.isFinite(Number(macroF1)) ? fmtNum(macroF1, 3) : "—",
        subtitle: "Promedio macro",
      },
      {
        title: "F1 weighted",
        value: Number.isFinite(Number(weightedF1)) ? fmtNum(weightedF1, 3) : "—",
        subtitle: "Promedio ponderado",
      },
      {
        title: "Datos usados",
        value: nInfo ? `${nInfo.base_rows ?? "?"} base + ${nInfo.human_rows ?? "?"} humano` : "—",
        subtitle: nInfo ? `w_base=${nInfo.base_weight} · w_human=${nInfo.human_weight}` : "",
      },
    ];
  }, [metricsObj]);

  const perClassRows = useMemo(() => {
    const pc = metricsObj?.per_class;
    if (!pc || typeof pc !== "object") return [];
    return Object.entries(pc).map(([cls, v]) => ({
      cls,
      precision: fmtNum(v?.precision, 3),
      recall: fmtNum(v?.recall, 3),
      f1: fmtNum(v?.["f1-score"], 3),
      support: Number.isFinite(Number(v?.support)) ? String(v.support) : "—",
    }));
  }, [metricsObj]);

  const featureRows = useMemo(() => {
    const pick = (arr) =>
      Array.isArray(arr)
        ? arr.slice(0, 20).map((d, idx) => ({ rank: idx + 1, feature: d.feature, importance: fmtNum(d.importance, 6) }))
        : [];

    if (Array.isArray(importanceShap) && importanceShap.length) return { method: "SHAP", rows: pick(importanceShap) };
    if (Array.isArray(importancePermutation) && importancePermutation.length)
      return { method: "PERMUTATION", rows: pick(importancePermutation) };
    return { method: null, rows: [] };
  }, [importancePermutation, importanceShap]);

  const container = {
    padding: "14px 14px",
  };

  const panel = {
    borderRadius: 18,
    border: "1px solid rgba(15,23,42,.12)",
    background: "#fff",
    boxShadow: "0 2px 12px rgba(15,23,42,.08)",
    padding: 14,
  };

  return (
    <div style={container}>
      <div style={{ display: "flex", alignItems: "flex-start", justifyContent: "space-between", gap: 12, flexWrap: "wrap" }}>
        <div>
          <div style={{ fontSize: 18, fontWeight: 1100, color: "#0f172a" }}>Modelo de predicción</div>
          <div style={{ marginTop: 4, fontSize: 13, fontWeight: 800, color: "#64748b" }}>
            Métricas, matriz de confusión y explicabilidad por versión
          </div>
        </div>

        <div style={{ display: "flex", alignItems: "center", gap: 10, flexWrap: "wrap" }}>
          {activeVersion ? <Badge tone="success">ACTIVO: {activeVersion}</Badge> : <Badge>Activo: —</Badge>}
          {loadingList ? <Badge>cargando modelos…</Badge> : null}
          {listErr ? <Badge tone="danger">{listErr}</Badge> : null}
        </div>
      </div>

      <div style={{ display: "grid", gridTemplateColumns: "320px 1fr", gap: 14, marginTop: 14 }}>
        {/* LEFT: listado / selector */}
        <div style={panel}>
          <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", gap: 10 }}>
            <div style={{ fontSize: 12, fontWeight: 1000, color: "#475569", textTransform: "uppercase", letterSpacing: 0.5 }}>
              Versiones
            </div>

            {/* z-index fix + colapsado + title */}
            <div style={{ position: "relative", zIndex: 60 }}>
              <select
                value={selected ?? ""}
                onChange={(e) => setSelected(e.target.value)}
                title={selected ?? ""}
                style={{
                  position: "relative",
                  zIndex: 61,
                  padding: "8px 10px",
                  borderRadius: 12,
                  border: "1px solid rgba(15,23,42,.12)",
                  fontWeight: 900,
                  color: "#0f172a",
                  background: "#fff",
                  cursor: "pointer",
                  maxWidth: 220,
                  overflow: "hidden",
                  textOverflow: "ellipsis",
                  whiteSpace: "nowrap",
                }}
              >
                {(models ?? []).map((m) => (
                  <option key={m.version} value={m.version}>
                    {(m.version?.length ?? 0) > 38 ? `${m.version.slice(0, 38)}…` : m.version}
                    {m.is_active ? " (ACTIVE)" : ""} · {m.status}
                  </option>
                ))}
              </select>
            </div>
          </div>

          {/* nombre completo visible (sin estorbar) */}
          {selected ? (
            <div style={{ marginTop: 10 }}>
              <Badge tone="purple">
                Seleccionado:&nbsp;
                <span
                  title={selected}
                  style={{
                    maxWidth: 240,
                    overflow: "hidden",
                    textOverflow: "ellipsis",
                    whiteSpace: "nowrap",
                    display: "inline-block",
                    fontWeight: 1100,
                  }}
                >
                  {selected}
                </span>
              </Badge>
            </div>
          ) : null}

          <div style={{ marginTop: 12, display: "grid", gap: 10 }}>
            {(models ?? []).map((m) => {
              const isSel = m.version === selected;
              const isAct = !!m.is_active;
              const tone = isAct ? "success" : "neutral";
              return (
                <button
                  key={m.version}
                  onClick={() => setSelected(m.version)}
                  style={{
                    textAlign: "left",
                    padding: "10px 12px",
                    borderRadius: 14,
                    border: isSel ? "1px solid rgba(124,58,237,.55)" : "1px solid rgba(15,23,42,.12)",
                    background: isSel ? "linear-gradient(135deg,#0b1220 0%, #4c1d95 100%)" : "#ffffff",
                    color: isSel ? "#fff" : "#0f172a",
                    cursor: "pointer",
                    boxShadow: isSel ? "0 10px 22px rgba(124,58,237,.25)" : "0 2px 10px rgba(15,23,42,.06)",
                  }}
                  title={m.version}
                >
                  <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", gap: 10 }}>
                    <div
                      style={{
                        fontWeight: 1100,
                        maxWidth: 200,
                        overflow: "hidden",
                        textOverflow: "ellipsis",
                        whiteSpace: "nowrap",
                      }}
                    >
                      {m.version}
                    </div>
                    <Badge tone={tone}>{isAct ? "ACTIVE" : m.status}</Badge>
                  </div>
                  <div
                    style={{
                      marginTop: 6,
                      fontSize: 12,
                      fontWeight: 800,
                      opacity: isSel ? 0.85 : 1,
                      color: isSel ? "rgba(255,255,255,.85)" : "#64748b",
                      overflow: "hidden",
                      textOverflow: "ellipsis",
                      whiteSpace: "nowrap",
                    }}
                    title={m.artifact_path ?? ""}
                  >
                    {m.artifact_path ?? "—"}
                  </div>
                  <div
                    style={{
                      marginTop: 4,
                      fontSize: 12,
                      fontWeight: 800,
                      opacity: isSel ? 0.85 : 1,
                      color: isSel ? "rgba(255,255,255,.85)" : "#64748b",
                    }}
                  >
                    {m.date ? `fecha: ${new Date(m.date).toLocaleString()}` : ""}
                  </div>
                </button>
              );
            })}
          </div>
        </div>

        {/* RIGHT: detalle */}
        <div style={{ display: "grid", gap: 14 }}>
          <div style={panel}>
            <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", gap: 10, flexWrap: "wrap" }}>
              <div>
                <div style={{ fontSize: 12, fontWeight: 1000, color: "#475569", textTransform: "uppercase", letterSpacing: 0.5 }}>
                  Detalle del modelo
                </div>
                <div style={{ marginTop: 4, fontSize: 16, fontWeight: 1100, color: "#0f172a" }}>
                  {selected ?? "—"}
                </div>
              </div>

              <div style={{ display: "flex", gap: 10, flexWrap: "wrap" }}>
                {modelMeta?.is_active ? <Badge tone="success">ACTIVO</Badge> : <Badge>inactivo</Badge>}
                {modelMeta?.status ? (
                  <Badge tone={modelMeta.status === "DONE" ? "success" : modelMeta.status === "ERROR" ? "danger" : "purple"}>
                    {modelMeta.status}
                  </Badge>
                ) : null}
                {loadingDetail ? <Badge>cargando…</Badge> : null}
                {detailErr ? <Badge tone="danger">{detailErr}</Badge> : null}
              </div>
            </div>

            <div style={{ marginTop: 10, display: "flex", flexWrap: "wrap", gap: 10 }}>
              {cards.map((c) => (
                <Card key={c.title} title={c.title} value={c.value} subtitle={c.subtitle} />
              ))}
            </div>

            <div style={{ marginTop: 12, display: "grid", gridTemplateColumns: "1.1fr .9fr", gap: 14, alignItems: "start" }}>
              <div style={{ padding: 12, borderRadius: 16, border: "1px solid rgba(15,23,42,.10)", background: "rgba(15,23,42,.02)" }}>
                <div style={{ fontSize: 12, fontWeight: 1000, color: "#475569", textTransform: "uppercase", letterSpacing: 0.5 }}>
                  Matriz de confusión
                </div>
                <div style={{ marginTop: 8 }}>
                  <ConfusionMatrix matrix={confusion?.matrix} labels={metricsObj?.train_info?.classes ?? []} />
                </div>
              </div>

              <div style={{ padding: 12, borderRadius: 16, border: "1px solid rgba(15,23,42,.10)", background: "rgba(15,23,42,.02)" }}>
                <div style={{ fontSize: 12, fontWeight: 1000, color: "#475569", textTransform: "uppercase", letterSpacing: 0.5 }}>
                  Top features {featureRows.method ? `· ${featureRows.method}` : ""}
                </div>
                <div style={{ marginTop: 10 }}>
                  {featureRows.rows.length ? (
                    <SimpleTable
                      columns={[
                        { key: "rank", label: "#", align: "right" },
                        { key: "feature", label: "Feature" },
                        { key: "importance", label: "Importance", align: "right" },
                      ]}
                      rows={featureRows.rows}
                    />
                  ) : (
                    <div style={{ fontSize: 13, fontWeight: 800, color: "#64748b" }}>
                      No hay importancias guardadas todavía (PERMUTATION/SHAP).
                    </div>
                  )}
                </div>
              </div>
            </div>
          </div>

          <div style={panel}>
            <div style={{ fontSize: 12, fontWeight: 1000, color: "#475569", textTransform: "uppercase", letterSpacing: 0.5 }}>
              Métricas por clase
            </div>
            <div style={{ marginTop: 10 }}>
              {perClassRows.length ? (
                <SimpleTable
                  columns={[
                    { key: "cls", label: "Clase" },
                    { key: "precision", label: "Precision", align: "right" },
                    { key: "recall", label: "Recall", align: "right" },
                    { key: "f1", label: "F1", align: "right" },
                    { key: "support", label: "Support", align: "right" },
                  ]}
                  rows={perClassRows}
                />
              ) : (
                <div style={{ fontSize: 13, fontWeight: 800, color: "#64748b" }}>
                  No hay datos de métricas por clase todavía.
                </div>
              )}
            </div>

            <div style={{ marginTop: 12, display: "flex", gap: 10, flexWrap: "wrap" }}>
              {latestMetrics?.dataset_ref ? <Badge>dataset_ref: {latestMetrics.dataset_ref}</Badge> : null}
              {latestMetrics?.notes ? <Badge>notes: {latestMetrics.notes}</Badge> : null}
              {latestMetrics?.computed_at ? <Badge>computed: {new Date(latestMetrics.computed_at).toLocaleString()}</Badge> : null}
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}