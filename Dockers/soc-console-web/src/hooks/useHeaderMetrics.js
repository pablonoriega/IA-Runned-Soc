import { useEffect, useState } from "react";
import { fetchSocMetrics } from "../services/api";

export function useHeaderMetrics() {
  const [loading, setLoading] = useState(false);
  const [err, setErr] = useState("");
  const [data, setData] = useState(null);

  useEffect(() => {
    let alive = true;

    (async () => {
      setLoading(true);
      setErr("");
      try {
        const res = await fetchSocMetrics({ days: 7 });
        if (!alive) return;
        setData(res);
      } catch (e) {
        if (!alive) return;
        setErr(String(e));
        setData(null);
      } finally {
        if (!alive) return;
        setLoading(false);
      }
    })();

    return () => { alive = false; };
  }, []);

  return { loading, err, data };
}