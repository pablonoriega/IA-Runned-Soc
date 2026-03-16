import React from "react";
import { ui } from "./socStatus.styles";
import { assetTone, fmtAsset, sevTone, statusTone, normStatus } from "./socStatus.utils";

import Badge from "../common/Badge";
import EmptyState from "../common/EmptyState";

export default function AssetsSection({ assets, expandedAsset, setExpandedAsset, onSelectAlert }) {
  const list = assets ?? [];
  const noAssets = list.length === 0;

  if (noAssets) {
    return (
      <EmptyState
        title="Sin assets"
        description="No hay assets para mostrar."
        tone="slate"
      />
    );
  }

  return (
    <>
      <div style={ui.row}>
        <div style={{ fontSize: 16, fontWeight: 1100, color: "#0f172a" }}>Assets</div>
        <div style={{ fontSize: 12, fontWeight: 950, color: "#475569" }}>
          Click an asset to expand · Click an alert to open detail
        </div>
      </div>

      <div style={ui.assetsGrid}>
        {list.map(({ asset_type, alerts: assetAlerts }) => {
          const items = assetAlerts ?? [];
          const activeCount = items.length;
          const tone = assetTone(activeCount);
          const expanded = expandedAsset === asset_type;

          const onCardClick = () => setExpandedAsset(expanded ? null : asset_type);

          const stateTone =
            activeCount === 0 ? "green" :
            tone === "crit" ? "red" :
            tone === "high" ? "rose" :
            tone === "mid" ? "amber" : "cyan";

          return (
            <div
              key={asset_type}
              style={ui.assetCard(tone, expanded)}
              onClick={!expanded ? onCardClick : undefined}
              onMouseEnter={(e) => {
                if (!expanded) e.currentTarget.style.transform = "translateY(-1px)";
              }}
              onMouseLeave={(e) => {
                e.currentTarget.style.transform = "translateY(0px)";
              }}
              role="button"
              tabIndex={0}
              onKeyDown={(e) => {
                if (e.key === "Enter" || e.key === " ") onCardClick();
              }}
            >
              <div style={{ display: "flex", justifyContent: "space-between", gap: 12, alignItems: "flex-start" }}>
                <div>
                  <div style={ui.tiny}>ASSET</div>
                  <div style={ui.big(expanded)}>{fmtAsset(asset_type)}</div>

                  <div style={{ marginTop: 8 }}>
                    <Badge tone="slate">Alerts: {activeCount}</Badge>
                  </div>
                </div>

                <div style={{ textAlign: "right" }}>
                  <div style={ui.tiny}>STATE</div>

                  <div style={{ marginTop: 8 }}>
                    <Badge tone={stateTone}>{activeCount === 0 ? "OK" : "ALERTS"}</Badge>
                  </div>

                  {expanded && (
                    <div style={ui.closeRow}>
                      <button
                        type="button"
                        style={ui.closeBtn}
                        onClick={(e) => {
                          e.stopPropagation();
                          setExpandedAsset(null);
                        }}
                      >
                        Collapse
                      </button>
                    </div>
                  )}
                </div>
              </div>

              {expanded && (
                <div style={ui.listWrap}>
                  <div style={ui.listHeader}>
                    <div>ID</div>
                    <div>Type / Phase</div>
                    <div>Sev</div>
                    <div>Status</div>
                    <div>Assigned</div>
                  </div>

                  <div style={ui.listBody}>
                    {items.length === 0 ? (
                      <div style={{ padding: 12 }}>
                        <EmptyState title="No alerts" description="Este asset no tiene alertas." tone="slate" />
                      </div>
                    ) : (
                      items.map((al) => (
                        <div
                          key={al.alert_id}
                          style={ui.listRow}
                          onClick={(e) => {
                            e.stopPropagation();
                            onSelectAlert?.(al.alert_id);
                          }}
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
                              {al.src_ip ? `IP: ${al.src_ip}` : ""}
                              {al.asset_criticality ? ` · criticality: ${al.asset_criticality}` : ""}
                            </div>
                          </div>

                          <div>
                            <Badge tone={sevTone(al.severity)}>S{al.severity}</Badge>
                          </div>

                          <div>
                            <Badge tone={statusTone(al.status)}>{normStatus(al.status)}</Badge>
                          </div>

                          <div style={{ fontWeight: 950, color: "#0f172a" }}>
                            {al.assigned_to ? String(al.assigned_to) : <span style={ui.muted}>-</span>}
                          </div>
                        </div>
                      ))
                    )}
                  </div>
                </div>
              )}
            </div>
          );
        })}
      </div>
    </>
  );
}