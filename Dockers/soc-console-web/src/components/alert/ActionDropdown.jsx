import React, { useEffect, useMemo, useRef, useState } from "react";
import { ui } from "./alertDetail.styles";

const ACTIONS = [
  { value: "ignore", label: "ignore" },
  { value: "investigate", label: "investigate" },
  { value: "block_ip", label: "block_ip" },
  { value: "reset_credentials", label: "reset_credentials" },
  { value: "disable_account", label: "disable_account" },
  { value: "isolate_host", label: "isolate_host" },
  { value: "escalate_incident", label: "escalate_incident" },
];

export default function ActionDropdown({ value, onChange, suggested }) {
  const [open, setOpen] = useState(false);
  const [hover, setHover] = useState(null);
  const ref = useRef(null);

  const suggestedSet = useMemo(() => new Set((suggested ?? []).map((x) => x.action)), [suggested]);

  const suggestedItems = useMemo(() => {
    const allowed = new Set(ACTIONS.map((a) => a.value));
    return (suggested ?? []).filter((x) => allowed.has(x.action)).slice(0, 3);
  }, [suggested]);

  const otherItems = useMemo(() => ACTIONS.filter((a) => !suggestedSet.has(a.value)), [suggestedSet]);

  const currentLabel = useMemo(() => {
    return ACTIONS.find((a) => a.value === value)?.label ?? value ?? "";
  }, [value]);

  useEffect(() => {
    function onDocDown(e) {
      if (!ref.current) return;
      if (!ref.current.contains(e.target)) setOpen(false);
    }
    document.addEventListener("mousedown", onDocDown);
    return () => document.removeEventListener("mousedown", onDocDown);
  }, []);

  return (
    <div ref={ref} style={ui.ddWrap}>
      <button
        type="button"
        style={ui.ddBtn}
        onClick={() => setOpen((v) => !v)}
        aria-haspopup="listbox"
        aria-expanded={open}
      >
        <span>{currentLabel}</span>
        <span style={{ opacity: 0.6, fontWeight: 900 }}>▾</span>
      </button>

      {open && (
        <div style={ui.ddMenu} role="listbox">
          {suggestedItems.length > 0 && (
            <>
              <div style={ui.ddGroup}>Suggested (IA)</div>
              {suggestedItems.map((s) => (
                <div
                  key={`s-${s.action}`}
                  style={{
                    ...ui.ddItem,
                    ...(hover === `s-${s.action}` ? ui.ddItemHover : null),
                  }}
                  onMouseEnter={() => setHover(`s-${s.action}`)}
                  onMouseLeave={() => setHover(null)}
                  onClick={() => {
                    onChange(s.action);
                    setOpen(false);
                  }}
                  role="option"
                  aria-selected={value === s.action}
                >
                  <span>{s.action}</span>
                  <span style={ui.ddRight}>
                    <span style={ui.badge("cyan")}>{(Number(s.prob) * 100).toFixed(1)}% IA</span>
                  </span>
                </div>
              ))}
            </>
          )}

          <div style={ui.ddGroup}>Todas las acciones</div>
          {otherItems.map((a) => (
            <div
              key={a.value}
              style={{
                ...ui.ddItem,
                borderBottom: "none",
                ...(hover === a.value ? ui.ddItemHover : null),
              }}
              onMouseEnter={() => setHover(a.value)}
              onMouseLeave={() => setHover(null)}
              onClick={() => {
                onChange(a.value);
                setOpen(false);
              }}
              role="option"
              aria-selected={value === a.value}
            >
              <span>{a.label}</span>
              <span style={{ opacity: 0.6, fontWeight: 900 }}>{value === a.value ? "✓" : ""}</span>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}