import React, { useMemo } from "react";
import TopK from "../components/alert/TopK.jsx";
import Events from "../components/alert/Events.jsx";
import ActionDropdown from "../components/alert/ActionDropdown.jsx";
import { ui } from "../components/alert/alertDetail.styles";
import { useAlertDetail } from "../hooks/useAlertDetail";

import Badge from "../components/common/Badge.jsx";
import EmptyState from "../components/common/EmptyState.jsx";

function sevTone(sev) {
  if (sev >= 5) return "red";
  if (sev === 4) return "rose";
  if (sev === 3) return "amber";
  if (sev === 2) return "green";
  return "mint";
}

function statusTone(status) {
  if (status === "PENDING_HUMAN") return "amber";
  if (status === "IN_PROGRESS") return "blue";
  if (status === "DONE") return "green";
  if (status === "REJECTED") return "slate";
  if (status === "ERROR") return "red";
  return "violet";
}

export default function AlertDetailPage({ alertId, onBack }) {
  const d = useAlertDetail(alertId);

  const a = d.alert;
  const p = a?.raw_payload ?? {};
  const sev = a?.severity ?? p.severity ?? 1;

  const tone = useMemo(() => sevTone(Number(sev)), [sev]);
  const stTone = useMemo(() => statusTone(a?.status ?? "NEW"), [a?.status]);

  // Si está CLOSED (o viene closed_at), no se puede decidir
  const isClosed = Boolean(a?.closed_at) || String(a?.status ?? "").toUpperCase() === "CLOSED";
  const hasHumanDecision = Boolean(a?.human_decision || a?.human_final_action);

  if (!a) {
    return (
      <div style={{ padding: 16 }}>
        {d.err ? (
          <EmptyState title="Error" description={String(d.err)} tone="red" />
        ) : (
          <EmptyState title="Cargando..." description="Obteniendo detalle de la alerta." tone="slate" />
        )}
      </div>
    );
  }

  return (
    <div style={ui.page}>
      <div style={ui.topRow}>
        <button onClick={onBack} style={ui.back}>
          ← Back
        </button>
        <Badge tone={stTone}>{a.status}</Badge>
      </div>

      <div style={ui.header}>
        <h2 style={ui.title}>Alert #{a.alert_id}</h2>
        <div style={ui.sub}>
          <Badge tone={tone}>Severity {a.severity}</Badge>{" "}
          <Badge tone="blue">{a.alert_type}</Badge>{" "}
          <Badge tone="slate">{a.attack_phase}</Badge>
        </div>
      </div>

      {d.err && <div style={ui.err}>{String(d.err)}</div>}

      <div style={ui.grid}>
        {/* CONTEXTO */}
        <div style={ui.card}>
          <h3 style={ui.h3}>Contexto</h3>

          <div style={ui.kv}>
            <div>
              <div style={ui.key}>Tipo/Fase</div>
              <div style={ui.val}>
                {a.alert_type ?? p.alert_type ?? "-"} / {a.attack_phase ?? p.attack_phase ?? "-"}
              </div>
            </div>

            <div>
              <div style={ui.key}>Activo</div>
              <div style={ui.val}>
                {a.asset_type ?? p.asset_type ?? "-"} ({a.asset_criticality ?? p.asset_criticality ?? "-"})
              </div>
            </div>

            <div>
              <div style={ui.key}>IP</div>
              <div style={ui.val}>
                {a.src_ip ?? p.src_ip ?? "-"} ({a.ip_reputation ?? p.ip_reputation ?? "-"})
              </div>
            </div>

            <div>
              <div style={ui.key}>Repeat offender</div>
              <div style={ui.val}>{String(a.repeat_offender ?? p.repeat_offender ?? false)}</div>
            </div>

            <div>
              <div style={ui.key}>Event count</div>
              <div style={ui.val}>
                {a.event_count ?? p.event_count ?? "-"} / {a.time_window_minutes ?? p.time_window_minutes ?? "-"} min
              </div>
            </div>

            <div>
              <div style={ui.key}>Detección</div>
              <div style={ui.val}>
                {a.detection_source ?? p.detection_source ?? "-"} (conf: {a.confidence ?? p.confidence ?? "-"})
              </div>
            </div>

            <div>
              <div style={ui.key}>Timestamp</div>
              <div style={ui.val}>{a.timestamp_utc ?? p.timestamp_utc ?? "-"}</div>
            </div>
          </div>

          <div style={ui.aiBox}>
            <div
              style={{
                display: "flex",
                alignItems: "center",
                justifyContent: "space-between",
                gap: 10,
                marginBottom: 8,
              }}
            >
              <h3 style={{ ...ui.h3, margin: 0 }}>AI explanation</h3>
              <Badge tone="cyan">IA</Badge>
            </div>

            {a.ai_explanation ? (
              <div style={ui.aiText}>{a.ai_explanation}</div>
            ) : (
              <EmptyState
                title="Sin explicación IA"
                description="Esta alerta no trae explicación del modelo."
                tone="slate"
              />
            )}
          </div>
        </div>

        {/* MODELO + HITL */}
        <div style={ui.card}>
          <h3 style={ui.h3}>Modelo</h3>

          <div style={{ display: "flex", gap: 8, flexWrap: "wrap", marginBottom: 10 }}>
            <Badge tone="blue">Action: {a.model_recommended_action ?? "-"}</Badge>
            <Badge tone="violet">
              Conf: {a.model_confidence != null ? Number(a.model_confidence).toFixed(3) : "-"}
            </Badge>
          </div>

          <TopK topk={a.model_top_k} />

          <h3 style={{ ...ui.h3, marginTop: 14 }}>Decisión (HITL)</h3>

          {/* Si está CLOSED: no se puede decidir; solo mostramos el bloque inferior */}
          {isClosed ? (
            hasHumanDecision ? (
              <div
                style={{
                  marginTop: 12,
                  background: "#f8fafc",
                  padding: 12,
                  borderRadius: 14,
                  border: "1px solid rgba(15,23,42,.08)",
                }}
              >
                <div style={{ display: "flex", gap: 8, flexWrap: "wrap", marginBottom: 8 }}>
                  <Badge tone="slate">Human: {a.human_decision ?? "-"}</Badge>
                  <Badge tone="green">Action: {a.human_final_action ?? "-"}</Badge>
                </div>

                <div style={{ fontSize: 13, color: "#0f172a" }}>
                  <div>
                    <b>Actor:</b> {a.human_decided_by ?? "-"}
                  </div>
                  <div>
                    <b>At:</b> {a.human_decided_at ?? "-"}
                  </div>
                  <div>
                    <b>Comment:</b> {a.human_reason ?? "-"}
                  </div>
                </div>
              </div>
            ) : (
              <div style={{ marginTop: 12 }}>
                <EmptyState
                  title="Cerrada sin decisión humana"
                  description="Esta alerta está cerrada pero no hay decisión HITL registrada."
                  tone="slate"
                />
              </div>
            )
          ) : (
            <>
              {/* Si NO está CLOSED: mostramos el formulario + botones */}
              <div style={ui.formGrid}>
                <div>
                  <div style={{ fontSize: 12, color: "#475569", fontWeight: 700, marginBottom: 6 }}>Operador</div>
                  <input value={d.operator} onChange={(e) => d.setOperator(e.target.value)} style={ui.input} />
                </div>

                <div>
                  <div style={{ fontSize: 12, color: "#475569", fontWeight: 700, marginBottom: 6 }}>Acción final</div>
                  <ActionDropdown value={d.selectedAction} onChange={d.setSelectedAction} suggested={d.suggested} />
                </div>

                <div style={{ gridColumn: "1 / span 2" }}>
                  <div style={{ fontSize: 12, color: "#475569", fontWeight: 700, marginBottom: 6 }}>Comentario</div>
                  <input value={d.comment} onChange={(e) => d.setComment(e.target.value)} style={ui.inputWide} />
                </div>
              </div>

              <div style={ui.actions}>
                <button
                  disabled={d.saving}
                  onClick={() => d.decide("ACCEPT")}
                  style={{ ...ui.accept, opacity: d.saving ? 0.7 : 1 }}
                >
                  Accept
                </button>
                <button
                  disabled={d.saving}
                  onClick={() => d.decide("REJECT")}
                  style={{ ...ui.reject, opacity: d.saving ? 0.7 : 1 }}
                >
                  Reject
                </button>
              </div>

              {/* Si ya existe decisión humana aunque no esté closed, la mostramos igual */}
              {hasHumanDecision ? (
                <div
                  style={{
                    marginTop: 12,
                    background: "#f8fafc",
                    padding: 12,
                    borderRadius: 14,
                    border: "1px solid rgba(15,23,42,.08)",
                  }}
                >
                  <div style={{ display: "flex", gap: 8, flexWrap: "wrap", marginBottom: 8 }}>
                    <Badge tone="slate">Human: {a.human_decision ?? "-"}</Badge>
                    <Badge tone="green">Action: {a.human_final_action ?? "-"}</Badge>
                  </div>

                  <div style={{ fontSize: 13, color: "#0f172a" }}>
                    <div>
                      <b>Actor:</b> {a.human_decided_by ?? "-"}
                    </div>
                    <div>
                      <b>At:</b> {a.human_decided_at ?? "-"}
                    </div>
                    <div>
                      <b>Comment:</b> {a.human_reason ?? "-"}
                    </div>
                  </div>
                </div>
              ) : (
                <div style={{ marginTop: 12 }}>
                  <EmptyState
                    title="Sin decisión humana"
                    description="Aún no hay una decisión HITL registrada para esta alerta."
                    tone="slate"
                  />
                </div>
              )}
            </>
          )}
        </div>
      </div>

      <div style={{ marginTop: 12 }}>
        <Events events={d.events ?? []} />
      </div>
    </div>
  );
}