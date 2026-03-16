import React from "react";
import { ui } from "./socStatus.styles";
import { STATUS_OPTIONS } from "./socStatus.utils";
import Badge from "../common/Badge";

export default function SocStatusHeader({
  statusFilter,
  setStatusFilter,
  alertsRawCount,
  alertsCount,
}) {
  return (
    <div style={ui.header}>
      <h2 style={ui.title}>SOC Status</h2>
      <div style={ui.sub}>Operators & Assets (click an alert to open detail).</div>
    </div>
  );
}