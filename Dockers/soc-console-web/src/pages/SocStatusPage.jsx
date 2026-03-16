// src/pages/SocStatusPage.jsx
import React, { useMemo } from "react";
import { ui } from "../components/socStatus/socStatus.styles";
import SocStatusHeader from "../components/socStatus/SocStatusHeader";
import OperatorsSection from "../components/socStatus/OperatorsSection";
import AssetsSection from "../components/socStatus/AssetsSection";
import { ASSET_TYPES, normStatus } from "../components/socStatus/socStatus.utils";
import { useSocStatus } from "../hooks/useSocStatus";

import Badge from "../components/common/Badge";
import EmptyState from "../components/common/EmptyState";

export default function SocStatusPage({ onBack, onSelect }) {
  const s = useSocStatus();

  const alertsFiltered = useMemo(() => {
    if (s.statusFilter === "ALL") return s.alertsRaw ?? [];
    return (s.alertsRaw ?? []).filter((a) => normStatus(a?.status) === s.statusFilter);
  }, [s.alertsRaw, s.statusFilter]);

  const allOpsCount = (s.opsActive?.length ?? 0) + (s.opsInactive?.length ?? 0);

  const hasAnyData =
    (s.alertsRaw?.length ?? 0) > 0 ||
    (s.opsActive?.length ?? 0) > 0 ||
    (s.opsInactive?.length ?? 0) > 0;

  return (
    <div style={ui.page}>
      <div style={ui.topRow}>
        <button onClick={onBack} style={ui.back}>← Back</button>
        <button
          onClick={s.reload}
          disabled={s.loading}
          style={{ ...ui.btn, opacity: s.loading ? 0.7 : 1 }}
        >
          {s.loading ? "Refreshing..." : "Refresh"}
        </button>
      </div>

      <SocStatusHeader
        statusFilter={s.statusFilter}
        setStatusFilter={s.setStatusFilter}
        alertsRawCount={(s.alertsRaw ?? []).length}
        alertsCount={alertsFiltered.length}
      />

      {s.err ? (
        <div style={{ marginTop: 12 }}>
          <EmptyState title="Error cargando SOC Status" description={String(s.err)} tone="red" />
        </div>
      ) : !hasAnyData && s.loading ? (
        <div style={{ marginTop: 12 }}>
          <EmptyState title="Cargando SOC Status..." description="Obteniendo operadores y alertas." tone="slate" />
        </div>
      ) : null}

      <div style={ui.shell}>
        <div style={ui.nav}>
          <button
            style={ui.navItem(s.section === "operators")}
            onClick={() => s.setSection("operators")}
          >
            <span>Operators</span>
            <Badge tone="slate">{allOpsCount}</Badge>
          </button>

          <button
            style={ui.navItem(s.section === "assets")}
            onClick={() => s.setSection("assets")}
          >
            <span>Assets</span>
            <Badge tone="slate">{ASSET_TYPES.length}</Badge>
          </button>
        </div>

        <div style={ui.main}>
          {s.section === "operators" ? (
            allOpsCount === 0 && !s.loading ? (
              <EmptyState
                title="Sin operadores"
                description="No hay operadores activos o inactivos para mostrar."
                tone="slate"
              />
            ) : (
              <OperatorsSection
                opsActive={s.opsActive}
                opsInactive={s.opsInactive}
                selectedOperator={s.selectedOperator}
                onSelectOperator={s.setSelectedOperator}
                opAlerts={s.opAlerts}
                opLoading={s.opLoading}
                onSelectAlert={(alertId) => onSelect?.(alertId)}
                pendingByOperator={s.pendingByOperator}

                // SLA real
                slaLoading={s.slaLoading}
                slaErr={s.slaErr}
                slaStats={s.slaStats}
                slaClosedItems={s.slaClosedItems}
              />
            )
          ) : (s.assets ?? []).every((x) => (x.alerts?.length ?? 0) === 0) && !s.loading ? (
            <EmptyState
              title="Sin alertas en Assets"
              description="No hay PENDING_HUMAN para ningún asset."
              tone="slate"
            />
          ) : (
            <AssetsSection
              assets={s.assets}
              expandedAsset={s.expandedAsset}
              setExpandedAsset={s.setExpandedAsset}
              onSelectAlert={(alertId) => onSelect?.(alertId)}
            />
          )}
        </div>
      </div>
    </div>
  );
}