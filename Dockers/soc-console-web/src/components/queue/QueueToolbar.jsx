import React, { useMemo } from "react";
import { styles } from "./queue.styles";
import { dotColorForTone, statusTone } from "./queue.utils";

export default function QueueToolbar({ status, setStatus, refresh, loading, err }) {
  const headerBadgeTone = useMemo(() => statusTone(status), [status]);

  return (
    <div style={styles.toolbar}>
      <div style={{ display: "flex", flexDirection: "column", gap: 6, minWidth: 220 }}>
        <div style={{ fontSize: 13, opacity: 0.95, fontWeight: 700 }}>MiniSOC • Work Queue</div>
        <div style={{ fontSize: 12, opacity: 0.75 }}>
          Filtra y revisa alertas. Selecciona una para ver detalle y decidir.
        </div>
      </div>

      <div style={styles.field}>
        <span style={styles.label}>Status</span>
        <select value={status} onChange={(e) => setStatus(e.target.value)} style={styles.input}>
          <option value="ALL">TODAS</option>
          <option value="PROCESSING">PROCESSING</option>
          <option value="PENDING_HUMAN">PENDING HUMAN</option>
          <option value="CLOSED">CLOSED</option>
        </select>
      </div>

      <button onClick={refresh} disabled={loading} style={{ ...styles.button, opacity: loading ? 0.7 : 1 }}>
        {loading ? "Cargando..." : "Refresh"}
      </button>

      <span style={styles.badge(headerBadgeTone)}>
        <span style={styles.pillDot(dotColorForTone(headerBadgeTone))} />
        {status === "ALL" ? "TODAS" : status}
      </span>

      {err && <span style={styles.err}>{err}</span>}
    </div>
  );
}