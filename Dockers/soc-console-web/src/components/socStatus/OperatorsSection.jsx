import React, { useMemo, useState } from "react";
import { ui } from "./socStatus.styles";
import {
  calcCapacity,
  capacityLabel,
  capacityTone,
  fmtDuration,
  humanizeToken,
  normStatus,
  statusTone,
} from "./socStatus.utils";

export default function OperatorsSection({
  opsActive,
  opsInactive,
  selectedOperator,
  onSelectOperator,
  opAlerts,
  opLoading,

  // ✅ SLA props nuevos
  slaLoading,
  slaErr,
  slaStats,
  slaClosedItems,

  onSelectAlert,
  pendingByOperator,
}) {
  const [tab, setTab] = useState("active"); // active | inactive
  const [q, setQ] = useState("");

  const list = tab === "active" ? (opsActive ?? []) : (opsInactive ?? []);

  const filtered = useMemo(() => {
    const needle = q.trim().toLowerCase();
    if (!needle) return list;

    return (list ?? []).filter((o) => {
      const name = String((o.display_name ?? o.username ?? "")).toLowerCase();
      const user = String(o.username ?? "").toLowerCase();
      const role = String(o.role ?? "").toLowerCase();
      const shift = String(o.shift_name ?? "").toLowerCase();
      const id = String(o.operator_id ?? "");
      return (
        name.includes(needle) ||
        user.includes(needle) ||
        role.includes(needle) ||
        shift.includes(needle) ||
        id.includes(needle)
      );
    });
  }, [list, q]);

  return (
    <>
      <div style={ui.row}>
        <div style={{ fontSize: 16, fontWeight: 1100, color: "#0f172a" }}>
          Operators
        </div>
        <div style={{ display: "flex", gap: 8, flexWrap: "wrap" }}>
          <span style={ui.badge("green")}>Active: {(opsActive ?? []).length}</span>
          <span style={ui.badge("slate")}>Inactive: {(opsInactive ?? []).length}</span>
        </div>
      </div>

      <div style={ui.opLayout}>
        {/* LEFT */}
        <div style={ui.opLeftCard}>
          <div style={ui.tabs}>
            <button type="button" style={ui.tab(tab === "active")} onClick={() => setTab("active")}>
              <span>Active</span>
              <span style={ui.navPill}>{(opsActive ?? []).length}</span>
            </button>
            <button type="button" style={ui.tab(tab === "inactive")} onClick={() => setTab("inactive")}>
              <span>Inactive</span>
              <span style={ui.navPill}>{(opsInactive ?? []).length}</span>
            </button>
          </div>

          <input value={q} onChange={(e) => setQ(e.target.value)} placeholder="Search operator…" style={ui.search} />

          {filtered.map((o) => {
            const selected = selectedOperator?.operator_id === o.operator_id;
            const display = (o.display_name ?? o.username) || "Unknown";

            const cap = calcCapacity(o);
            const capTone = capacityTone(cap.pct);

            return (
              <div
                key={o.operator_id}
                style={ui.opItem(selected)}
                onClick={() => onSelectOperator(o)}
                role="button"
                tabIndex={0}
                onKeyDown={(e) => {
                  if (e.key === "Enter" || e.key === " ") onSelectOperator(o);
                }}
                title="Open operator"
              >
                <div style={{ minWidth: 0 }}>
                  <div style={ui.opName}>
                    {display}{" "}
                    <span style={{ color: "#64748b", fontWeight: 1000 }}>#{o.operator_id}</span>
                  </div>
                  <div style={ui.opSub}>{(o.shift_name ?? "-") + " · " + (o.role ?? "-")}</div>
                </div>

                <div style={ui.opRightLite}>
                  <span style={ui.badge(capTone)}>{capacityLabel(cap.assigned, cap.max, cap.pct)}</span>
                  {o.on_call ? <span style={ui.badge("amber")}>On-call</span> : null}
                </div>
              </div>
            );
          })}

          {filtered.length === 0 && (
            <div style={{ color: "#64748b", fontWeight: 900, padding: 10 }}>
              No operators found.
            </div>
          )}
        </div>

        {/* RIGHT */}
        <div style={ui.rightStack}>
          <OperatorDetailCard operator={selectedOperator} pendingByOperator={pendingByOperator} />
          <OperatorSkillsCard operator={selectedOperator} />

          <SlaSummaryCard
            operator={selectedOperator}
            slaLoading={slaLoading}
            slaErr={slaErr}
            slaStats={slaStats}
            slaClosedItems={slaClosedItems}
          />

          <RecentAlertsCard
            operator={selectedOperator}
            alerts={opAlerts}
            loading={opLoading}
            onSelectAlert={onSelectAlert}
          />
        </div>
      </div>
    </>
  );
}

function OperatorDetailCard({ operator, pendingByOperator }) {
  if (!operator) {
    return (
      <div style={ui.card}>
        <div style={ui.cardTitle}>Operator</div>
        <div style={{ color: "#64748b", fontWeight: 950 }}>
          Select an operator to view details.
        </div>
      </div>
    );
  }

  const cap = calcCapacity(operator);
  const capTone = capacityTone(cap.pct);

  const pendingCount = pendingByOperator?.get(operator.operator_id) ?? 0;

  return (
    <div style={ui.card}>
      <div style={{ display: "flex", justifyContent: "space-between", gap: 12, flexWrap: "wrap" }}>
        <div>
          <div style={{ fontSize: 18, fontWeight: 1100, color: "#0f172a" }}>
            {operator.display_name ?? operator.username}{" "}
            <span style={{ color: "#64748b", fontWeight: 1100 }}>#{operator.operator_id}</span>
          </div>

          <div style={{ marginTop: 8, display: "flex", gap: 8, flexWrap: "wrap" }}>
            <span style={ui.badge(operator.is_active ? "green" : "slate")}>
              {operator.is_active ? "Active" : "Inactive"}
            </span>
            <span style={ui.badge(operator.on_call ? "amber" : "cyan")}>
              {operator.on_call ? "On-call" : "Available"}
            </span>
            <span style={ui.badge("slate")}>{operator.shift_name ?? "Shift: -"}</span>
            <span style={ui.badge("violet")}>{operator.role ?? "Role: -"}</span>
          </div>
        </div>

        <div style={{ textAlign: "right" }}>
          <div style={{ fontSize: 12, fontWeight: 950, color: "#475569", textTransform: "uppercase" }}>
            Current load
          </div>
          <div style={{ marginTop: 8, display: "flex", gap: 8, justifyContent: "flex-end", flexWrap: "wrap" }}>
            <span style={ui.badge(capTone)}>{capacityLabel(cap.assigned, cap.max, cap.pct)}</span>
            <span style={ui.badge("slate")}>Resolve target: {fmtDuration(operator.sla_resolve_seconds)}</span>
            <span style={ui.badge("cyan")}>Pending: {pendingCount}</span>
          </div>
        </div>
      </div>

      <div style={{ marginTop: 12, ...ui.kv }}>
        <div style={ui.kvItem}>
          <div style={ui.kvK}>Username</div>
          <div style={ui.kvV}>{operator.username ?? "-"}</div>
        </div>
        <div style={ui.kvItem}>
          <div style={ui.kvK}>Email</div>
          <div style={ui.kvV}>{operator.email ?? "-"}</div>
        </div>
        <div style={ui.kvItem}>
          <div style={ui.kvK}>Timezone</div>
          <div style={ui.kvV}>{operator.timezone ?? "-"}</div>
        </div>
        <div style={ui.kvItem}>
          <div style={ui.kvK}>Business hours only</div>
          <div style={ui.kvV}>{String(!!operator.business_hours_only)}</div>
        </div>
      </div>
    </div>
  );
}

function OperatorSkillsCard({ operator }) {
  const skills = operator?.skills ?? null;
  const alertTypes = Array.isArray(skills?.alert_types) ? skills.alert_types : [];
  const phases = Array.isArray(skills?.attack_phases) ? skills.attack_phases : [];
  const minSev = skills?.min_severity ?? null;

  return (
    <div style={ui.card}>
      <div style={ui.row}>
        <div style={ui.cardTitle}>Coverage</div>
        {operator && minSev != null ? <span style={ui.badge("violet")}>Min severity: S{minSev}</span> : null}
      </div>

      {!operator ? (
        <div style={{ color: "#64748b", fontWeight: 950 }}>Select an operator to see skills coverage.</div>
      ) : (
        <>
          <div style={{ fontSize: 12, fontWeight: 1000, color: "#475569", textTransform: "uppercase", letterSpacing: 0.4 }}>
            Attack phases
          </div>
          <div style={{ marginTop: 8, ...ui.chipsWrap }}>
            {phases.length
              ? phases.map((p) => <span key={p} style={ui.chip}>{humanizeToken(p)}</span>)
              : <span style={ui.chipMuted}>No phases</span>}
          </div>

          <div style={{ marginTop: 12, fontSize: 12, fontWeight: 1000, color: "#475569", textTransform: "uppercase", letterSpacing: 0.4 }}>
            Alert types
          </div>
          <div style={{ marginTop: 8, ...ui.chipsWrap }}>
            {alertTypes.length
              ? alertTypes.map((t) => <span key={t} style={ui.chip}>{humanizeToken(t)}</span>)
              : <span style={ui.chipMuted}>No alert types</span>}
          </div>
        </>
      )}
    </div>
  );
}

function SlaSummaryCard({ operator, slaLoading, slaErr, slaStats, slaClosedItems }) {
  const closed = slaStats?.total ?? 0;          // total CLOSED en DB
  const considered = slaStats?.considered ?? 0; // usados para stats
  const compliancePct = slaStats?.compliance_pct;

  const ok =
    considered > 0 && compliancePct != null
      ? Math.round((considered * Number(compliancePct)) / 100)
      : 0;

  const breaches = Math.max(0, considered - ok);

  return (
    <div style={ui.card}>
      <div style={ui.row}>
        <div style={ui.cardTitle}>SLA compliance</div>
        {operator ? (
          <span style={ui.badge("slate")}>
            Target: {fmtDuration(operator?.sla_resolve_seconds)}
          </span>
        ) : null}
      </div>

      {!operator ? (
        <div style={{ color: "#64748b", fontWeight: 950 }}>
          Select an operator to see SLA compliance.
        </div>
      ) : slaLoading ? (
        <div style={{ color: "#64748b", fontWeight: 900 }}>Loading SLA…</div>
      ) : slaErr ? (
        <div style={{ color: "#991b1b", fontWeight: 900, fontSize: 12 }}>
          {String(slaErr)}
        </div>
      ) : !slaStats ? (
        <div style={{ color: "#64748b", fontWeight: 900, fontSize: 12 }}>
          No SLA data (no CLOSED alerts found for this operator in this window).
        </div>
      ) : (
        <>
          <div style={{ marginTop: 10, display: "flex", gap: 8, flexWrap: "wrap" }}>
            <span style={ui.badge("cyan")}>Closed: {closed}</span>
            <span style={ui.badge("slate")}>Considered: {considered}</span>
            <span style={ui.badge("green")}>OK: {ok}</span>
            <span style={ui.badge("rose")}>Breaches: {breaches}</span>
            <span style={ui.badge("violet")}>
              Compliance: {compliancePct != null ? `${Number(compliancePct).toFixed(1)}%` : "-"}
            </span>
          </div>

          <div style={{ marginTop: 10, ...ui.kv }}>
            <div style={ui.kvItem}>
              <div style={ui.kvK}>Avg resolve</div>
              <div style={ui.kvV}>{fmtDuration(slaStats.avg_seconds)}</div>
            </div>
            <div style={ui.kvItem}>
              <div style={ui.kvK}>Median</div>
              <div style={ui.kvV}>{fmtDuration(slaStats.median_seconds)}</div>
            </div>
            <div style={ui.kvItem}>
              <div style={ui.kvK}>P90</div>
              <div style={ui.kvV}>{fmtDuration(slaStats.p90_seconds)}</div>
            </div>
          </div>

          <div style={{ marginTop: 12, color: "#64748b", fontWeight: 900, fontSize: 12 }}>
            Latest closed (page): {(slaClosedItems ?? []).length}
          </div>
        </>
      )}
    </div>
  );
}

function RecentAlertsCard({ operator, alerts, loading, onSelectAlert }) {
  return (
    <div style={ui.card}>
      <div style={ui.row}>
        <div style={ui.cardTitle}>Pending Human (assigned)</div>
        <div style={{ display: "flex", gap: 8, flexWrap: "wrap" }}>
          <span style={ui.badge("slate")}>Loaded: {(alerts ?? []).length}</span>
        </div>
      </div>

      {!operator ? (
        <div style={{ color: "#64748b", fontWeight: 950 }}>Select an operator to view assigned alerts.</div>
      ) : (
        <div style={ui.tableWrap}>
          <div style={ui.tableHead}>
            <div>ID</div>
            <div>Type / Phase</div>
            <div>Severity</div>
            <div>Status</div>
          </div>

          <div style={ui.tableBody}>
            {(alerts ?? []).map((al) => (
              <div
                key={al.alert_id}
                style={ui.tableRow}
                onClick={() => onSelectAlert?.(al.alert_id)}
                title="Open alert detail"
                role="button"
                tabIndex={0}
                onKeyDown={(e) => {
                  if (e.key === "Enter" || e.key === " ") onSelectAlert?.(al.alert_id);
                }}
              >
                <div style={ui.mono}>#{al.alert_id}</div>

                <div style={{ minWidth: 0 }}>
                  <div style={{ fontWeight: 1100, color: "#0f172a", whiteSpace: "nowrap", overflow: "hidden", textOverflow: "ellipsis" }}>
                    {al.alert_type} <span style={ui.muted}>· {al.attack_phase}</span>
                  </div>
                  <div style={{ fontSize: 12, fontWeight: 900, color: "#64748b", marginTop: 2 }}>
                    {al.asset_type ? `asset: ${al.asset_type}` : ""}
                    {al.src_ip ? ` · IP: ${al.src_ip}` : ""}
                  </div>
                </div>

                <div>
                  <span style={ui.badge("violet")}>S{al.severity}</span>
                </div>

                <div>
                  <span style={ui.badge(statusTone(al.status))}>{normStatus(al.status)}</span>
                </div>
              </div>
            ))}

            {(alerts ?? []).length === 0 && (
              <div style={{ padding: 12, color: "#64748b", fontWeight: 950 }}>
                No PENDING_HUMAN alerts assigned to this operator.
              </div>
            )}
          </div>
        </div>
      )}
    </div>
  );
}