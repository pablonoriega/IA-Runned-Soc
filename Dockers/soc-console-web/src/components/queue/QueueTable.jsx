import React from "react";
import { styles } from "./queue.styles";
import { dotColorForTone, severityTone, statusTone } from "./queue.utils";

function SortHeader({ sort, toggleSort, colKey, label, alignRight }) {
  const active = sort.key === colKey;
  const arrow = !active ? "↕" : sort.dir === "asc" ? "↑" : "↓";

  return (
    <button
      type="button"
      onClick={() => toggleSort(colKey)}
      style={{
        ...styles.thBtn,
        width: "100%",
        justifyContent: alignRight ? "flex-end" : "flex-start",
      }}
      title={`Ordenar por ${label}`}
    >
      <span>{label}</span>
      <span style={{ ...styles.sortIcon, ...(active ? styles.sortActive : null) }}>
        <span style={{ fontSize: 11 }}>{arrow}</span>
      </span>
    </button>
  );
}

export default function QueueTable({ items, selectedId, onSelect, sort, toggleSort }) {
  return (
    <div style={styles.tableCard}>
      <table style={styles.table}>
        <thead>
          <tr>
            <th style={styles.th}><SortHeader sort={sort} toggleSort={toggleSort} colKey="alert_id" label="ID" /></th>
            <th style={styles.th}><SortHeader sort={sort} toggleSort={toggleSort} colKey="alert_type" label="Tipo" /></th>
            <th style={styles.th}><SortHeader sort={sort} toggleSort={toggleSort} colKey="attack_phase" label="Fase" /></th>
            <th style={styles.th}><SortHeader sort={sort} toggleSort={toggleSort} colKey="status" label="Status" /></th>

            <th style={{ ...styles.th, textAlign: "right" }}>
              <SortHeader sort={sort} toggleSort={toggleSort} colKey="severity" label="Sev" alignRight />
            </th>

            <th style={styles.th}>
              <SortHeader sort={sort} toggleSort={toggleSort} colKey="model_recommended_action" label="Acción (modelo)" />
            </th>

            <th style={{ ...styles.th, textAlign: "right" }}>
              <SortHeader sort={sort} toggleSort={toggleSort} colKey="model_confidence" label="Conf" alignRight />
            </th>

            <th style={{ ...styles.th, width: 1 }} />
          </tr>
        </thead>

        <tbody>
          {items.map((a) => {
            const isSelected = a.alert_id === selectedId;
            const sevT = severityTone(a.severity);

            const rowStatus = a.status ?? "-";
            const rowStatusTone = rowStatus === "-" ? "white" : statusTone(rowStatus);

            return (
              <tr
                key={a.alert_id}
                style={{
                  ...styles.tr,
                  background: isSelected ? "rgba(124,58,237,.08)" : "transparent",
                  cursor: "pointer",
                }}
                onMouseEnter={(e) => {
                  e.currentTarget.style.background = isSelected ? "rgba(124,58,237,.10)" : "rgba(15,23,42,.03)";
                }}
                onMouseLeave={(e) => {
                  e.currentTarget.style.background = isSelected ? "rgba(124,58,237,.08)" : "transparent";
                }}
                onClick={() => onSelect(a.alert_id)}
              >
                <td style={styles.td}><b>{a.alert_id}</b></td>
                <td style={styles.td}>{a.alert_type}</td>
                <td style={styles.td}>{a.attack_phase}</td>

                <td style={styles.td}>
                  <span style={styles.badge(rowStatusTone)}>
                    <span style={styles.pillDot(dotColorForTone(rowStatusTone))} />
                    {rowStatus}
                  </span>
                </td>

                <td style={{ ...styles.td, textAlign: "right" }}>
                  <span style={styles.badge(sevT)}>
                    <span style={styles.pillDot(dotColorForTone(sevT))} />
                    {a.severity}
                  </span>
                </td>

                <td style={styles.td}>
                  {a.model_recommended_action ? (
                    <span style={styles.badge("lilac")}>{a.model_recommended_action}</span>
                  ) : (
                    <span style={styles.badge("white")}>-</span>
                  )}
                </td>

                <td style={{ ...styles.td, textAlign: "right" }}>
                  {a.model_confidence != null ? (
                    <span style={styles.badge("blue")}>{a.model_confidence.toFixed(2)}</span>
                  ) : (
                    <span style={styles.badge("white")}>-</span>
                  )}
                </td>

                <td style={{ ...styles.td, textAlign: "right" }}>
                  <button
                    onClick={(e) => {
                      e.stopPropagation();
                      onSelect(a.alert_id);
                    }}
                    style={styles.rowButton}
                  >
                    Review →
                  </button>
                </td>
              </tr>
            );
          })}

          {items.length === 0 && (
            <tr>
              <td colSpan="8" style={styles.empty}>No hay alertas para este filtro.</td>
            </tr>
          )}
        </tbody>
      </table>
    </div>
  );
}