import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import { fetchAlerts } from "../services/api";
import { makeAlertsWsUrl } from "../services/ws";

function normalizeStr(v) {
  return (v ?? "").toString().toLowerCase();
}

export function useQueue({ initialStatus = "ALL" } = {}) {
  const [status, setStatus] = useState(initialStatus);
  const [items, setItems] = useState([]);
  const [err, setErr] = useState("");
  const [loading, setLoading] = useState(false);
  const [sort, setSort] = useState({ key: "alert_id", dir: "desc" });

  const refreshTimerRef = useRef(null);

  const buildParams = useCallback((s) => ({
    limit: 25,
    offset: 0,
    ...(s !== "ALL" ? { status: s } : {}),
  }), []);

  const load = useCallback(async () => {
    setLoading(true);
    setErr("");
    try {
      const data = await fetchAlerts(buildParams(status));
      setItems(data.items ?? []);
    } catch (e) {
      setErr(String(e));
    } finally {
      setLoading(false);
    }
  }, [status, buildParams]);

  const refreshSilent = useCallback(async () => {
    try {
      const data = await fetchAlerts(buildParams(status));
      setItems(data.items ?? []);
    } catch {}
  }, [status, buildParams]);

  useEffect(() => { load(); }, [load]);

  const sortedItems = useMemo(() => {
    const arr = [...items];
    const { key, dir } = sort;
    const mult = dir === "asc" ? 1 : -1;

    arr.sort((a, b) => {
      const av = a?.[key];
      const bv = b?.[key];

      if (key === "alert_id" || key === "severity" || key === "model_confidence") {
        const an = Number(av ?? 0);
        const bn = Number(bv ?? 0);
        if (an < bn) return -1 * mult;
        if (an > bn) return 1 * mult;
        return 0;
      }

      const as = normalizeStr(av);
      const bs = normalizeStr(bv);
      if (as < bs) return -1 * mult;
      if (as > bs) return 1 * mult;
      return 0;
    });

    return arr;
  }, [items, sort]);

  const toggleSort = useCallback((key) => {
    setSort((s) => {
      if (s.key !== key) return { key, dir: "asc" };
      return { key, dir: s.dir === "asc" ? "desc" : "asc" };
    });
  }, []);

  // WS subscribe + refresh on INSERT + UPDATE
  useEffect(() => {
    const wsUrl = makeAlertsWsUrl();

    let ws;
    let alive = true;
    let retry = 500;

    const scheduleRefresh = () => {
      if (refreshTimerRef.current) return;
      refreshTimerRef.current = setTimeout(async () => {
        refreshTimerRef.current = null;
        await refreshSilent();
      }, 250);
    };

    const connect = () => {
      ws = new WebSocket(wsUrl);

      ws.onopen = () => {
        retry = 500;
        ws.send(JSON.stringify({ type: "subscribe", status }));
      };

      ws.onmessage = (ev) => {
        try {
          const msg = JSON.parse(ev.data);
          if (msg.event === "ALERT_INSERTED" || msg.event === "ALERT_STATUS_CHANGED") scheduleRefresh();
        } catch {}
      };

      ws.onclose = () => {
        if (!alive) return;
        setTimeout(connect, retry);
        retry = Math.min(retry * 2, 8000);
      };

      ws.onerror = () => {
        try { ws.close(); } catch {}
      };
    };

    connect();

    return () => {
      alive = false;
      if (refreshTimerRef.current) {
        clearTimeout(refreshTimerRef.current);
        refreshTimerRef.current = null;
      }
      try { ws?.close(); } catch {}
    };
  }, [status, refreshSilent]);

  return { status, setStatus, items: sortedItems, err, loading, sort, toggleSort, refresh: load };
}