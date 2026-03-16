import React from "react";
import QueueToolbar from "../components/queue/QueueToolbar";
import QueueTable from "../components/queue/QueueTable";
import { styles } from "../components/queue/queue.styles";
import { useQueue } from "../hooks/useQueue";

export default function QueuePage({ onSelect, selectedId }) {
  const q = useQueue();

  return (
    <div style={styles.page}>
      <QueueToolbar status={q.status} setStatus={q.setStatus} refresh={q.refresh} loading={q.loading} err={q.err} />
      <div style={styles.sectionTitle}>Work Queue</div>
      <QueueTable items={q.items} selectedId={selectedId} onSelect={onSelect} sort={q.sort} toggleSort={q.toggleSort} />
    </div>
  );
}