import React from "react";

const TONES = {
  slate: { bg: "rgba(15,23,42,.08)", fg: "#0f172a", br: "rgba(15,23,42,.12)" },
  green: { bg: "rgba(34,197,94,.14)", fg: "#166534", br: "rgba(34,197,94,.25)" },
  cyan: { bg: "rgba(6,182,212,.12)", fg: "#155e75", br: "rgba(6,182,212,.24)" },
  amber: { bg: "rgba(245,158,11,.16)", fg: "#92400e", br: "rgba(245,158,11,.28)" },
  rose: { bg: "rgba(244,63,94,.12)", fg: "#9f1239", br: "rgba(244,63,94,.24)" },
  red: { bg: "rgba(239,68,68,.14)", fg: "#991b1b", br: "rgba(239,68,68,.30)" },
  blue: { bg: "rgba(59,130,246,.12)", fg: "#1d4ed8", br: "rgba(59,130,246,.20)" },
  violet: { bg: "rgba(124,58,237,.12)", fg: "#5b21b6", br: "rgba(124,58,237,.20)" },
  ink: { bg: "rgba(2,6,23,.06)", fg: "#0f172a", br: "rgba(2,6,23,.10)" },
  white: { bg: "rgba(255,255,255,.85)", fg: "#0f172a", br: "rgba(15,23,42,.18)" },
};

export default function Badge({
  tone = "slate",
  children,
  style,
  title,
  leftDot, // optional color string "#06b6d4"
}) {
  const c = TONES[tone] ?? TONES.slate;

  return (
    <span
      title={title}
      style={{
        display: "inline-flex",
        alignItems: "center",
        gap: 6,
        padding: "6px 10px",
        borderRadius: 999,
        background: c.bg,
        color: c.fg,
        border: `1px solid ${c.br}`,
        fontSize: 12,
        fontWeight: 900,
        lineHeight: 1,
        whiteSpace: "nowrap",
        ...style,
      }}
    >
      {leftDot ? (
        <span
          style={{
            width: 8,
            height: 8,
            borderRadius: 999,
            background: leftDot,
            boxShadow: "0 0 0 3px rgba(0,0,0,.04)",
          }}
        />
      ) : null}
      {children}
    </span>
  );
}