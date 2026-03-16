import { getApiBase } from "./api";

export function makeAlertsWsUrl() {
  const apiBase = getApiBase(); // http://localhost:7000
  return apiBase.replace("http", "ws") + "/ws/alerts";
}