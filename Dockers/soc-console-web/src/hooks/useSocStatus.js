// src/hooks/useSocStatus.js
import { useEffect, useMemo, useState } from "react";
import { fetchAlerts, fetchOperators, fetchOperatorSla } from "../services/api";
import { ASSET_TYPES, normStatus } from "../components/socStatus/socStatus.utils";

export function useSocStatus() {
  const [section, setSection] = useState("operators");
  const [loading, setLoading] = useState(false);
  const [err, setErr] = useState("");

  const [opsActive, setOpsActive] = useState([]);
  const [opsInactive, setOpsInactive] = useState([]);

  const [alertsRaw, setAlertsRaw] = useState([]);

  const [expandedAsset, setExpandedAsset] = useState(null);
  const [selectedOperator, setSelectedOperator] = useState(null);

  // dropdown
  const [statusFilter, setStatusFilter] = useState("ALL");

  const [slaLoading, setSlaLoading] = useState(false);
  const [slaErr, setSlaErr] = useState("");
  const [slaData, setSlaData] = useState(null);

  async function loadAll() {
    setLoading(true);
    setErr("");
    try {
      const [aOps, iOps, pendingAlerts] = await Promise.all([
        fetchOperators({ active: "true" }),
        fetchOperators({ active: "false" }),
        fetchAlerts({ limit: 200, offset: 0, status: "PENDING_HUMAN" }),
      ]);

      const act = aOps?.items ?? [];
      const ina = iOps?.items ?? [];

      setOpsActive(act);
      setOpsInactive(ina);

      setSelectedOperator((prev) => {
        if (prev?.operator_id != null) return prev;
        return act.length ? act[0] : ina.length ? ina[0] : null;
      });

      setAlertsRaw(pendingAlerts?.items ?? []);
    } catch (e) {
      setErr(String(e));
      setAlertsRaw([]);
      setOpsActive([]);
      setOpsInactive([]);
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    loadAll();
  }, []);

  useEffect(() => {
    const id = selectedOperator?.operator_id;

    if (!id) {
      setSlaData(null);
      setSlaErr("");
      setSlaLoading(false);
      return;
    }

    let alive = true;

    (async () => {
      setSlaLoading(true);
      setSlaErr("");
      try {
        const data = await fetchOperatorSla(id, { limit: 50, offset: 0 });
        if (!alive) return;
        setSlaData(data);
      } catch (e) {
        if (!alive) return;
        setSlaErr(String(e));
        setSlaData(null);
      } finally {
        if (!alive) return;
        setSlaLoading(false);
      }
    })();

    return () => {
      alive = false;
    };
  }, [selectedOperator?.operator_id]);

  const pendingByOperator = useMemo(() => {
    const m = new Map();
    for (const a of alertsRaw ?? []) {
      if (normStatus(a?.status) !== "PENDING_HUMAN") continue;

      const raw = a?.assigned_to;
      if (raw == null) continue;

      const id = Number(raw);
      if (!Number.isFinite(id)) continue;

      m.set(id, (m.get(id) ?? 0) + 1);
    }
    return m;
  }, [alertsRaw]);

  const opAlerts = useMemo(() => {
    const id = selectedOperator?.operator_id;
    if (!id) return [];
    return (alertsRaw ?? [])
      .filter(
        (a) =>
          normStatus(a?.status) === "PENDING_HUMAN" &&
          Number(a?.assigned_to) === Number(id)
      )
      .slice()
      .sort((a, b) => Number(b.alert_id ?? 0) - Number(a.alert_id ?? 0));
  }, [alertsRaw, selectedOperator?.operator_id]);

  const assets = useMemo(() => {
    const list = (alertsRaw ?? []).slice();
    const m = new Map();
    for (const t of ASSET_TYPES) m.set(t, []);
    for (const al of list) {
      const t = String(al.asset_type ?? "");
      if (m.has(t)) m.get(t).push(al);
    }
    return ASSET_TYPES.map((t) => ({ asset_type: t, alerts: m.get(t) ?? [] }));
  }, [alertsRaw]);

  const slaStats = slaData?.stats ?? null;
  const slaClosedItems = slaData?.items ?? [];

  return {
    section,
    setSection,
    loading,
    err,
    opsActive,
    opsInactive,
    alertsRaw,
    expandedAsset,
    setExpandedAsset,
    selectedOperator,
    setSelectedOperator,

    pendingByOperator,
    opAlerts,

    opLoading: false,
    statusFilter,
    setStatusFilter,
    assets,

    slaLoading,
    slaErr,
    slaData,
    slaStats,
    slaClosedItems,

    reload: loadAll,
  };
}