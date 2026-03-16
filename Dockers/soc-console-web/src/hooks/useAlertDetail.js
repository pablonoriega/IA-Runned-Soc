import { useCallback, useEffect, useMemo, useState } from "react";
import { fetchAlert, fetchEvents, fetchOperator, postDecision } from "../services/api";

function normalizeTopK(alertObj) {
  const topk = Array.isArray(alertObj?.model_top_k)
    ? alertObj.model_top_k
    : (alertObj?.model_top_k?.top_k ?? []);
  return Array.isArray(topk) ? topk : [];
}

function topSuggestedWithProb(alertObj, n = 3) {
  const topk = normalizeTopK(alertObj)
    .filter((x) => x?.action)
    .map((x) => ({ action: String(x.action), prob: Number(x.prob ?? 0) }))
    .sort((a, b) => (b.prob ?? 0) - (a.prob ?? 0));

  const rec = alertObj?.model_recommended_action ? String(alertObj.model_recommended_action) : "";
  const out = [];

  const pushUnique = (action, prob) => {
    if (!action) return;
    if (out.some((x) => x.action === action)) return;
    out.push({ action, prob: Number(prob ?? 0) });
  };

  if (rec) {
    const hit = topk.find((x) => x.action === rec);
    pushUnique(rec, hit?.prob ?? 0);
  }
  for (const x of topk) pushUnique(x.action, x.prob);

  return out.slice(0, n);
}

export function useAlertDetail(alertId) {
  const [a, setA] = useState(null);
  const [events, setEvents] = useState(null);
  const [err, setErr] = useState("");
  const [operator, setOperator] = useState("analyst1");
  const [comment, setComment] = useState("");
  const [selectedAction, setSelectedAction] = useState("");
  const [saving, setSaving] = useState(false);

  const load = useCallback(async () => {
    setErr("");
    try {
      const detail = await fetchAlert(alertId);
      setA(detail);
      setSelectedAction(detail.model_recommended_action ?? "investigate");

      if (detail.assigned_to) {
        const op = await fetchOperator(detail.assigned_to);
        setOperator(op.username ?? op.display_name ?? String(detail.assigned_to));
      }

      const ev = await fetchEvents(alertId);
      setEvents(ev);
    } catch (e) {
      setErr(String(e));
    }
  }, [alertId]);

  useEffect(() => {
    if (!alertId) return;
    load();
  }, [alertId, load]);

  const decide = useCallback(async (decision) => {
    setSaving(true);
    setErr("");
    try {
      await postDecision(alertId, {
        decision,
        final_action: selectedAction,
        reason: comment || null,      
        decided_by: operator,         
      });
      await load();
    } catch (e) {
      setErr(String(e));
    } finally {
      setSaving(false);
    }
  }, [alertId, selectedAction, operator, comment, load]);

  const suggested = useMemo(() => topSuggestedWithProb(a, 3), [a]);

  return {
    alert: a,
    events,
    err,

    operator,
    setOperator,
    comment,
    setComment,
    selectedAction,
    setSelectedAction,

    saving,
    decide,
    reload: load,

    suggested,
  };
}