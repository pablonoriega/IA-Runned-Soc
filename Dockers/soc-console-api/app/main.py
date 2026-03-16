from fastapi import FastAPI, HTTPException, Query, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pathlib import Path

from typing import Optional, Dict, Set
import json
import os
import asyncio
import asyncpg 
from datetime import datetime, timezone
from zoneinfo import ZoneInfo
import uuid 
import requests
from .db import get_conn
from .models import *
from .sql import *
import random

app = FastAPI(title="SOC Console API", version="1.0")

# CORS (frontend)
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",
        "http://127.0.0.1:5173",
        "http://localhost:3001",
        "http://localhost:80",
        "http://localhost",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

N8N_EXEC_WEBHOOK = os.getenv("N8N_EXEC_WEBHOOK", "")  # e.g. http://n8n-minisoc:5678/webhook/execute-mitigation

@app.get("/health")
def health():
    return {"status": "ok"}

@app.get("/alerts", response_model=PagedAlerts)
def list_alerts(
    status: Optional[str] = Query(default="ALL"),
    severity_min: Optional[int] = Query(default=None, ge=1, le=5),
    severity_max: Optional[int] = Query(default=None, ge=1, le=5),
    asset_criticality: Optional[str] = Query(default=None),
    alert_type: Optional[str] = Query(default=None),
    attack_phase: Optional[str] = Query(default=None),
    repeat_offender: Optional[bool] = Query(default=None),
    assigned_to: Optional[str] = Query(default=None),
    limit: int = Query(default=25, ge=1, le=1000),
    offset: int = Query(default=0, ge=0),
):
    where = []
    params = []

    if status and status != "ALL":
        where.append("w.status = %s")
        params.append(status)

    if severity_min is not None:
        where.append("a.severity >= %s")
        params.append(severity_min)

    if severity_max is not None:
        where.append("a.severity <= %s")
        params.append(severity_max)

    if asset_criticality:
        where.append("a.asset_criticality = %s")
        params.append(asset_criticality)

    if alert_type:
        where.append("a.alert_type = %s")
        params.append(alert_type)

    if attack_phase:
        where.append("a.attack_phase = %s")
        params.append(attack_phase)

    if repeat_offender is not None:
        where.append("a.repeat_offender = %s")
        params.append(repeat_offender)

    if assigned_to is not None:
        where.append("w.assigned_to = %s")
        params.append(str(assigned_to))

    where_sql = (" WHERE " + " AND ".join(where)) if where else ""

    order_sql = " ORDER BY a.alert_id DESC "
    if status == "CLOSED":
        order_sql = " ORDER BY w.closed_at DESC NULLS LAST, a.alert_id DESC "

    q_count = COUNT_ALERTS_BASE + where_sql
    q_list = LIST_ALERTS_BASE + where_sql + order_sql + " LIMIT %s OFFSET %s"

    with get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute(q_count, params)
            total = cur.fetchone()["total"]

            cur.execute(q_list, params + [limit, offset])
            rows = cur.fetchall()

    items = [AlertSummary(**{**r, "repeat_offender": bool(r["repeat_offender"])}) for r in rows]
    return {"items": items, "limit": limit, "offset": offset, "total": total}

def _count_open_assigned_alerts(cur, assigned_to: str) -> int:
    # Reutiliza la base del endpoint /alerts
    # "abiertas" = no CLOSED (incluye NEW/PENDING_HUMAN/IN_PROGRESS/etc.)
    q = COUNT_ALERTS_BASE + " WHERE w.assigned_to = %s AND w.status <> 'CLOSED'"
    cur.execute(q, (assigned_to,))
    row = cur.fetchone()
    return int(row["total"] or 0)

@app.get("/alerts/{alert_id}", response_model=AlertDetail)
def get_alert(alert_id: int):
    with get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute(DETAIL_ALERT, (alert_id,))
            row = cur.fetchone()

    if not row:
        raise HTTPException(status_code=404, detail="Alert not found")

    for k in ["is_business_hours","geo_anomaly","repeat_offender","is_privileged_account","isolation_supported"]:
        if k in row and row[k] is not None:
            row[k] = bool(row[k])

    return AlertDetail(**row)

@app.get("/alerts/{alert_id}/events", response_model=list[EventItem])
def get_events(alert_id: int):
    with get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute(LIST_EVENTS, (alert_id,))
            rows = cur.fetchall()

    return [EventItem(**r) for r in rows]

@app.post("/alerts/{alert_id}/decision")
def decide(alert_id: int, body: DecisionRequest):

    new_status = "CLOSED"

    with get_conn() as conn:
        with conn.cursor() as cur:

            cur.execute("SELECT status FROM alert_workflow WHERE alert_id=%s", (alert_id,))
            w = cur.fetchone()
            if not w:
                raise HTTPException(status_code=404, detail="Workflow not found for alert_id")

            current_status = w["status"]
            if current_status not in ["PENDING_HUMAN", "PROCESSING"]:
                raise HTTPException(status_code=409, detail=f"No se puede decidir en estado '{current_status}'")

            cur.execute(
                UPDATE_DECISION,
                (
                    new_status,
                    body.decision,
                    body.final_action,
                    body.reason,
                    body.decided_by,
                    alert_id
                )
            )

            updated = cur.fetchone()
            if not updated:
                raise HTTPException(status_code=500, detail="No se pudo actualizar la decisión")

            event_type = "HUMAN_APPROVED" if body.decision == "ACCEPT" else "HUMAN_REJECTED"
            details = {
                "decision": body.decision,
                "final_action": body.final_action,
                "reason": body.reason
            }
            cur.execute(
                INSERT_EVENT,
                (alert_id, event_type, body.decided_by, json.dumps(details))
            )

    return {"status": "ok", "alert_id": alert_id, "new_status": new_status}

PLAYBOOK_PATH = Path("/app/data/playbook.json")

@app.get("/playbook")
def get_playbook():
    if not PLAYBOOK_PATH.exists():
        raise HTTPException(status_code=404, detail=f"playbook.json no encontrado en {PLAYBOOK_PATH}")

    try:
        with PLAYBOOK_PATH.open("r", encoding="utf-8") as f:
            data = json.load(f)
        return JSONResponse(content=data)
    except json.JSONDecodeError as e:
        raise HTTPException(status_code=500, detail=f"playbook.json inválido (JSON mal formado): {e}")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"No se pudo leer playbook.json: {e}")


# WEBSOCKETS + POSTGRES LISTEN/NOTIFY (PARA AUTO-REFRESH UI)

PG_HOST = os.getenv("PG_HOST", "postgres")
PG_PORT = int(os.getenv("PG_PORT", "5432"))
PG_DB   = os.getenv("PG_DB", "socdb")
PG_USER = os.getenv("PG_USER", "soc")
PG_PASS = os.getenv("PG_PASS", "socpass")

DATABASE_URL = f"postgresql://{PG_USER}:{PG_PASS}@{PG_HOST}:{PG_PORT}/{PG_DB}"
CHANNEL = "alerts_channel"

class WSManager:
    def __init__(self):
        self.clients: Set[WebSocket] = set()
        self.filters: Dict[WebSocket, str] = {}

    async def connect(self, ws: WebSocket):
        await ws.accept()
        self.clients.add(ws)
        self.filters[ws] = "ALL"

    def disconnect(self, ws: WebSocket):
        self.clients.discard(ws)
        self.filters.pop(ws, None)

    def set_filter(self, ws: WebSocket, status: str):
        self.filters[ws] = status or "ALL"

    async def broadcast(self, message: dict):
        dead = set()
        payload = json.dumps(message)

        for ws in list(self.clients):
            wanted = self.filters.get(ws, "ALL")
            msg_status = message.get("status")

            # filtro server-side
            if wanted != "ALL" and msg_status != wanted:
                continue

            try:
                await ws.send_text(payload)
            except Exception:
                dead.add(ws)

        for ws in dead:
            self.disconnect(ws)

ws_manager = WSManager()

@app.websocket("/ws/alerts")
async def ws_alerts(ws: WebSocket):
    """
    Cliente envía: {"type":"subscribe","status":"ALL"|"NEW"|...}
    Servidor envía: eventos del trigger:
      - {"event":"ALERT_INSERTED","alert_id":..,"status":"NEW"}
      - {"event":"ALERT_STATUS_CHANGED","alert_id":..,"old_status":"..","status":".."}
    """
    await ws_manager.connect(ws)
    try:
        while True:
            raw = await ws.receive_text()
            try:
                msg = json.loads(raw)
            except Exception:
                continue

            if msg.get("type") == "subscribe":
                ws_manager.set_filter(ws, msg.get("status", "ALL"))
                await ws.send_text(json.dumps({"event": "SUBSCRIBED", "status": ws_manager.filters[ws]}))
    except WebSocketDisconnect:
        ws_manager.disconnect(ws)

async def pg_listen_task():
    conn: Optional[asyncpg.Connection] = None

    while True:
        try:
            conn = await asyncpg.connect(DATABASE_URL)

            def _handler(connection, pid, channel, payload):
                try:
                    data = json.loads(payload)
                except Exception:
                    data = {"event": "UNKNOWN", "raw": payload}

                asyncio.get_event_loop().create_task(ws_manager.broadcast(data))

            await conn.add_listener(CHANNEL, _handler)
            print(f"[soc-console-api] LISTEN {CHANNEL}")

            while True:
                await asyncio.sleep(3600)

        except Exception as e:
            print("[soc-console-api] PG LISTEN error:", e)
            await asyncio.sleep(2)

        finally:
            if conn:
                try:
                    await conn.close()
                except Exception:
                    pass

@app.on_event("startup")
async def _startup_pg_listener():
    asyncio.create_task(pg_listen_task())

@app.get("/operators", response_model=OperatorsResponse)
def list_operators(active: bool = Query(default=True)):
    with get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute(LIST_OPERATORS, (active,))
            rows = cur.fetchall()

            for r in rows:
                op_id = str(r["operator_id"])
                r["currentAlarmsCount"] = _count_open_assigned_alerts(cur, op_id)

    # Normaliza booleans por si acaso + skills
    for r in rows:
        r["is_active"] = bool(r["is_active"])
        r["on_call"] = bool(r["on_call"])
        r["business_hours_only"] = bool(r["business_hours_only"])
        if r.get("skills") is None:
            r["skills"] = {}
        if r.get("currentAlarmsCount") is None:
            r["currentAlarmsCount"] = 0

    return {"items": rows}

@app.get("/operators/{operator_id}")
def get_operator(operator_id: int):
    with get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute(GET_OPERATOR, (operator_id,))
            row = cur.fetchone()

            if not row:
                raise HTTPException(status_code=404, detail="Operator not found")

            row["currentAlarmsCount"] = _count_open_assigned_alerts(cur, str(operator_id))

    row["is_active"] = bool(row["is_active"])
    row["on_call"] = bool(row["on_call"])
    row["business_hours_only"] = bool(row["business_hours_only"])
    if row.get("skills") is None:
        row["skills"] = {}
    if row.get("currentAlarmsCount") is None:
        row["currentAlarmsCount"] = 0

    return row


def _percentile(sorted_vals: list[int], p: float) -> Optional[int]:
    if not sorted_vals:
        return None
    # p en [0..1]
    idx = int(round((len(sorted_vals) - 1) * p))
    idx = max(0, min(idx, len(sorted_vals) - 1))
    return int(sorted_vals[idx])

@app.get("/operators/{operator_id}/sla", response_model=OperatorSlaResponse)
def operator_sla(
    operator_id: int,
    limit: int = Query(default=50, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
):
    # 1) target SLA del operador
    with get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute(GET_OPERATOR, (operator_id,))
            op = cur.fetchone()

            if not op:
                raise HTTPException(status_code=404, detail="Operator not found")

            target_seconds = int(op.get("sla_resolve_seconds") or 0)

            # 2) total closed
            cur.execute(COUNT_OPERATOR_CLOSED, (str(operator_id),))
            total = cur.fetchone()["total"]

            # 3) lista closed + resolve_seconds
            cur.execute(LIST_OPERATOR_CLOSED, (str(operator_id), limit, offset))
            rows = cur.fetchall()

    items = [OperatorSlaItem(**r) for r in rows]

    # 4) stats sobre los resolve_seconds de la página
    vals = [int(x.resolve_seconds) for x in items if x.resolve_seconds is not None and x.resolve_seconds >= 0]
    vals.sort()

    considered = len(vals)
    avg = (sum(vals) / considered) if considered else None
    median = _percentile(vals, 0.5)
    p90 = _percentile(vals, 0.9)

    compliance_pct = None
    if considered and target_seconds > 0:
        ok = sum(1 for v in vals if v <= target_seconds)
        compliance_pct = int(round((ok / considered) * 100))

    stats = OperatorSlaStats(
        total=total,
        considered=considered,
        target_seconds=target_seconds,
        avg_seconds=avg,
        median_seconds=median,
        p90_seconds=p90,
        compliance_pct=compliance_pct,
    )

    return {
        "items": items,
        "limit": limit,
        "offset": offset,
        "total": total,
        "stats": stats,
    }

def _stats_from_vals(vals: list[int]) -> SocMetricStats:
    vals = [int(v) for v in vals if v is not None and int(v) >= 0]
    vals.sort()
    n = len(vals)
    if n == 0:
        return SocMetricStats(considered=0, avg_seconds=None, median_seconds=None, p90_seconds=None)

    avg = sum(vals) / n
    median = _percentile(vals, 0.5)
    p90 = _percentile(vals, 0.9)
    return SocMetricStats(considered=n, avg_seconds=avg, median_seconds=median, p90_seconds=p90)

@app.get("/soc/metrics", response_model=SocMetricsResponse)
def soc_metrics(days: int = Query(default=7, ge=1, le=90)):
    with get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute(SOC_METRICS_RESOLVE, (days,))
            resolve_rows = cur.fetchall()
            resolve_vals = [r["resolve_seconds"] for r in resolve_rows]

            cur.execute(SOC_METRICS_ACK, (days,))
            ack_rows = cur.fetchall()
            ack_vals = [r["ack_seconds"] for r in ack_rows]

    return {
        "resolve": _stats_from_vals(resolve_vals),
        "ack": _stats_from_vals(ack_vals),
    }

@app.get("/model/latest", response_model=LatestModelResponse)
def get_latest_model():
    with get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute(GET_LATEST_MODEL)
            row = cur.fetchone()

    if not row:
        raise HTTPException(status_code=404, detail="No hay modelos registrados en ia_model")

    return LatestModelResponse(**row)

MADRID_TZ = ZoneInfo("Europe/Madrid")
N8N_RETRAIN_WEBHOOK = os.getenv("N8N_WEBHOOK_URL", "http://n8n-minisoc:5678/webhook/retrain-model")

@app.post("/retrain")
def retrain(req: RetrainRequest):
    if not req.run_immediately and not req.when:
        raise HTTPException(status_code=422, detail="when es obligatorio si run_immediately=false")

    version = f"retrain_{uuid.uuid4().hex[:8]}"

    # calcular fecha programada
    if req.run_immediately:
        scheduled_for = datetime.now(timezone.utc)
    else:
        try:
            dt_local = datetime.fromisoformat(req.when)  # datetime-local del frontend (sin TZ)
            dt_local = dt_local.replace(tzinfo=MADRID_TZ)
            scheduled_for = dt_local.astimezone(timezone.utc)
        except Exception:
            raise HTTPException(status_code=400, detail="Formato de fecha inválido")

    # 1) insertar en BDD
    with get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute(INSERT_RETRAIN, (version, scheduled_for, "soc_admin"))

            if req.dataset == "all_closed":
                cur.execute(UPDATE_ALL_CLOSED_RETRAIN, (version,))
            else:  # "rejected_only"
                cur.execute(UPDATE_REJECTED_ONLY_RETRAIN, (version, "REJECT"))

    # 2) NOTIFY N8N (best-effort)
    if N8N_RETRAIN_WEBHOOK:
        payload = {
            "type": "RETRAIN_MODEL",
            "version": version,
            "scheduled_for": scheduled_for.isoformat(),
            "run_immediately": bool(req.run_immediately),
            "when": req.when,        # puede ser None
            "dataset": req.dataset,  # no se guarda en BDD, pero n8n puede usarlo
        }

        try:
            r = requests.post(N8N_RETRAIN_WEBHOOK, json=payload, timeout=5)
            r.raise_for_status()
        except Exception as e:
            print("[retrain] n8n notify failed:", e)

    return {"status": "ok"}


N8N_TRAINING_GRADE_WEBHOOK = os.getenv("N8N_WEBHOOK_URL", "http://n8n-minisoc:5678/webhook/training-grade")

TRAINING_ACTIONS = [
    "ignore",
    "investigate",
    "block_ip",
    "reset_credentials",
    "disable_account",
    "isolate_host",
    "escalate_incident",
]

DETECTION_SOURCES = ["EDR","SIEM","IDS","NDR","Firewall","WAF","CloudTrail","EmailGW","DLP","IAM"]
COUNTRIES = ["ES","FR","DE","GB","IT","NL","US","BR","IN","CN","RU","PL","UA","TR","MX","AR"]

def _rand(arr):
    return arr[random.randint(0, len(arr)-1)]

def _clamp(x, lo=0.0, hi=1.0):
    return max(lo, min(hi, x))

def _gen_ip(private_only: bool):
    if private_only:
        return f"10.{random.randint(0,255)}.{random.randint(0,255)}.{random.randint(1,254)}"
    return f"{random.randint(1,223)}.{random.randint(0,255)}.{random.randint(0,255)}.{random.randint(1,254)}"

def generate_training_alert(config: dict) -> dict:
    phases = config.get("attack_phases") or []
    types  = config.get("alert_types") or []
    assets = config.get("asset_types") or []
    sevs   = config.get("severities") or []

    attack_phase = _rand(phases)
    alert_type   = _rand(types)
    asset_type   = _rand(assets)
    severity     = int(_rand(sevs))

    asset_criticality = _rand(["low","medium","high"])
    detection_source  = _rand(DETECTION_SOURCES)

    is_business_hours = bool(random.random() < 0.55)

    if asset_type == "workstation":
        exposure = "internet_facing" if random.random() < 0.03 else "internal"
    else:
        exposure = "internet_facing" if random.random() < 0.25 else "internal"

    src_ip = _gen_ip(exposure == "internal")
    src_country = "INTERNAL" if exposure == "internal" else _rand(COUNTRIES)
    geo_anomaly = False if exposure == "internal" else (random.random() < 0.12)

    if exposure == "internal":
        ip_rep = "bad" if random.random() < 0.02 else ("suspicious" if random.random() < 0.12 else "good")
    else:
        ip_rep = "bad" if random.random() < 0.20 else ("suspicious" if random.random() < 0.45 else "good")

    repeat_offender = (random.random() < 0.45) if ip_rep == "bad" else (random.random() < 0.12)
    previous_incidents_30d = max(0, min(15, int((2 if repeat_offender else 0) + random.random()*4)))

    conf = 0.45 + severity*0.08 + (0.05 if geo_anomaly else 0.0) + (0.07 if ip_rep == "bad" else 0.0) + random.random()*0.12
    confidence = round(_clamp(conf, 0.0, 0.99), 2)

    user_role = _rand(["standard","admin","service_account"])
    is_privileged_account = bool(user_role != "standard")

    isolation_supported = bool(random.random() < (0.55 if asset_type == "cloud_service" else 0.92))
    downtime_tolerance = _rand(["low","medium","high"])

    time_window_minutes = _rand([1,5,15,30,60,120,240])
    event_count = max(1, min(500, int(5 + random.random()*120)))

    return {
        "alert_type": alert_type,
        "attack_phase": attack_phase,
        "asset_type": asset_type,
        "asset_criticality": asset_criticality,
        "severity": severity,

        "timestamp_utc": datetime.now(timezone.utc).isoformat().replace("+00:00","Z"),
        "is_business_hours": is_business_hours,
        "detection_source": detection_source,
        "confidence": confidence,
        "src_ip": src_ip,
        "asset_exposure": exposure,
        "src_country": src_country,
        "geo_anomaly": geo_anomaly,
        "ip_reputation": ip_rep,
        "repeat_offender": repeat_offender,
        "previous_incidents_30d": previous_incidents_30d,
        "event_count": event_count,
        "time_window_minutes": time_window_minutes,
        "user_role": user_role,
        "is_privileged_account": is_privileged_account,
        "isolation_supported": isolation_supported,
        "downtime_tolerance": downtime_tolerance,
    }

# =========================
# TRAINING ENDPOINTS
# =========================

DEFAULT_OPERATOR_ID = "soc_operator"

@app.get("/training/sessions", response_model=TrainingSessionsResponse)
def training_list_sessions(
    limit: int = Query(default=50, ge=1, le=200),
):
    with get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute(TRAINING_LIST_SESSIONS, (DEFAULT_OPERATOR_ID, limit))
            rows = cur.fetchall()
    return {"items": rows}


@app.post("/training/sessions", response_model=TrainingCreateResponse)
def training_create_session(req: TrainingCreateRequest):
    cfg = req.config or {}
    for k in ["attack_phases","alert_types","asset_types","severities"]:
        if not cfg.get(k) or not isinstance(cfg.get(k), list) or len(cfg[k]) == 0:
            raise HTTPException(status_code=422, detail=f"config.{k} debe tener al menos 1 valor")

    operator_id = DEFAULT_OPERATOR_ID  

    with get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute(TRAINING_CREATE_SESSION, (operator_id, json.dumps(cfg), int(req.total_questions)))
            s = cur.fetchone()

            for _ in range(int(req.total_questions)):
                alert_payload = generate_training_alert(cfg)
                cur.execute(TRAINING_INSERT_ITEM, (s["session_id"], json.dumps(alert_payload), None))
                cur.fetchone()

    return s


@app.get("/training/sessions/{session_id}/next", response_model=TrainingNextItemResponse)
def training_next_item(session_id: int):
    with get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute(TRAINING_NEXT_ITEM, (session_id,))
            row = cur.fetchone()

    if not row:
        return {"item_id": None, "alert_payload": None}

    return {"item_id": row["item_id"], "alert_payload": row["alert_payload"]}


@app.post("/training/sessions/{session_id}/answer", response_model=TrainingAnswerResponse)
def training_answer(session_id: int, req: TrainingAnswerRequest):
    if req.operator_action not in TRAINING_ACTIONS:
        raise HTTPException(status_code=422, detail="operator_action inválido")

    if not N8N_TRAINING_GRADE_WEBHOOK:
        raise HTTPException(status_code=500, detail="N8N_TRAINING_GRADE_WEBHOOK no configurado")

    with get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute(TRAINING_GET_ITEM, (session_id, req.item_id))
            item = cur.fetchone()

            if not item:
                raise HTTPException(status_code=404, detail="Training item no encontrado")

            alert_payload = item["alert_payload"]

            # llamar a n8n para corregir
            webhook_payload = {
                "session_id": session_id,
                "item_id": req.item_id,
                "alert": alert_payload,
                "operator_action": req.operator_action,
                "operator_reason": req.operator_reason,
            }

            try:
                r = requests.post(N8N_TRAINING_GRADE_WEBHOOK, json=webhook_payload, timeout=25)
                r.raise_for_status()
                grade = r.json()
            except Exception as e:
                raise HTTPException(status_code=502, detail=f"Error llamando a n8n: {e}")

            # Normalizar respuesta esperada
            correct_action = str(grade.get("correct_action") or "")
            is_correct = bool(grade.get("is_correct"))
            score = float(grade.get("score") if grade.get("score") is not None else (1.0 if is_correct else 0.0))
            feedback_text = str(grade.get("feedback_text") or "Sin feedback")
            feedback_json = grade.get("feedback_json") or {}

            # guardar
            cur.execute(TRAINING_MARK_ITEM_ANSWERED, (session_id, req.item_id))

            cur.execute(
                TRAINING_INSERT_ANSWER,
                (
                    req.item_id,
                    session_id,
                    req.operator_action,
                    req.operator_reason,
                    correct_action,
                    is_correct,
                    score,
                    feedback_text,
                    json.dumps(feedback_json),
                ),
            )
            cur.fetchone()

            cur.execute(TRAINING_AGG_SESSION, (session_id,))
            agg = cur.fetchone() or {"answered": 0, "correct": 0, "wrong": 0}

            answered = int(agg["answered"] or 0)
            correct = int(agg["correct"] or 0)
            wrong = int(agg["wrong"] or 0)
            score_pct = float((correct / answered) * 100.0) if answered > 0 else 0.0

            cur.execute(TRAINING_UPDATE_SESSION_STATS, (correct, wrong, score_pct, session_id))

    return {
        "grade": {
            "correct_action": correct_action,
            "is_correct": is_correct,
            "score": score,
            "feedback_text": feedback_text,
            "feedback_json": feedback_json,
        },
        "progress": {
            "answered": answered,
            "correct": correct,
            "wrong": wrong,
            "score_pct": score_pct,
        },
    }


@app.post("/training/sessions/{session_id}/finish")
def training_finish(session_id: int):
    with get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute(TRAINING_FINISH_SESSION, (session_id,))
    return {"ok": True}


@app.get("/training/sessions/{session_id}", response_model=TrainingSessionDetailResponse)
def training_session_detail(session_id: int):
    with get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute(TRAINING_GET_SESSION, (session_id,))
            session = cur.fetchone()

            cur.execute(TRAINING_LIST_SESSION_ANSWERS, (session_id,))
            answers = cur.fetchall()

    return {"session": session, "answers": answers}

@app.get("/ml/models", response_model=MlModelsListResponse)
def ml_list_models():
    with get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute(ML_LIST_MODELS)
            rows = cur.fetchall()

    models = []
    active_version = None

    for r in rows:
        if isinstance(r, dict):
            version = r["version"]
            date = r["date"]
            status = r["status"]
            artifact_path = r["artifact_path"]
            is_active = bool(r["is_active"])
        else:
            (version, date, status, artifact_path, is_active) = r
            is_active = bool(is_active)

        if is_active:
            active_version = version

        models.append({
            "version": version,
            "date": date.isoformat() if date else None,
            "status": status,
            "artifact_path": artifact_path,
            "is_active": is_active,
        })

    return {"active_version": active_version, "models": models}


@app.get("/ml/models/{version}", response_model=MlModelDetailResponse)
def ml_model_detail(version: str):
    with get_conn() as conn:
        with conn.cursor() as cur:
            # 1) model meta
            cur.execute(ML_GET_MODEL, (version,))
            row = cur.fetchone()

            if not row:
                return {"model": None, "latest_metrics": None, "importances": {}}

            if isinstance(row, dict):
                v = row["version"]
                date = row["date"]
                status = row["status"]
                artifact_path = row["artifact_path"]
                is_active = bool(row["is_active"])
            else:
                (v, date, status, artifact_path, is_active) = row
                is_active = bool(is_active)

            model_obj = {
                "version": v,
                "date": date.isoformat() if date else None,
                "status": status,
                "artifact_path": artifact_path,
                "is_active": is_active,
            }

            # 2) latest metrics
            cur.execute(ML_GET_LATEST_METRICS, (version,))
            m = cur.fetchone()

            latest_metrics = None
            if m:
                if isinstance(m, dict):
                    computed_at = m["computed_at"]
                    split = m["split"]
                    threshold = m["threshold"]
                    metrics = m["metrics"] or {}
                    confusion = m["confusion"] or {}
                    dataset_ref = m["dataset_ref"]
                    notes = m["notes"]
                else:
                    (computed_at, split, threshold, metrics, confusion, dataset_ref, notes) = m
                    metrics = metrics or {}
                    confusion = confusion or {}

                latest_metrics = {
                    "computed_at": computed_at.isoformat() if computed_at else None,
                    "split": split,
                    "threshold": float(threshold) if threshold is not None else None,
                    "metrics": metrics,
                    "confusion": confusion,
                    "dataset_ref": dataset_ref,
                    "notes": notes,
                }

            # 3) latest importances by method (PERMUTATION + SHAP)
            importances = {}
            for method in ("PERMUTATION", "SHAP"):
                cur.execute(ML_GET_LATEST_IMPORTANCE, (version, method))
                imp = cur.fetchone()
                if not imp:
                    continue

                if isinstance(imp, dict):
                    importance = imp["importance"]
                else:
                    (_computed_at, _method, importance, _sample_info) = imp

                if importance:
                    importances[method] = importance

    return {"model": model_obj, "latest_metrics": latest_metrics, "importances": importances}