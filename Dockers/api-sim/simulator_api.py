from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
import os
import random
import json
from datetime import datetime, timezone
import requests
import psycopg2
import psycopg2.extras

app = FastAPI(title="SOC Alert Simulator API", version="1.0")

# ---------------------------
# Config (via env)
# ---------------------------
PG_HOST = os.getenv("PG_HOST", "soc-postgres")
PG_PORT = int(os.getenv("PG_PORT", "5432"))
PG_DB   = os.getenv("PG_DB", "socdb")
PG_USER = os.getenv("PG_USER", "soc")
PG_PASS = os.getenv("PG_PASS", "socpass")

# n8n webhook interno en la red docker
N8N_WEBHOOK_URL = os.getenv("N8N_WEBHOOK_URL", "http://n8n-minisoc:5678/webhook/soc-alert")

# ---------------------------
# Dominios
# ---------------------------
ALERT_TYPES = [
    "malware_detected","ransomware_activity","phishing_email","credential_dump_detected",
    "suspicious_login","brute_force_attempt","port_scan","command_and_control",
    "data_exfiltration","privilege_escalation"
]
ATTACK_PHASES = ["reconnaissance","initial_access","execution","lateral_movement","exfiltration"]
ASSET_TYPES = ["workstation","server","database","cloud_service"]
ASSET_CRIT = ["low","medium","high"]
DETECTION_SOURCES = ["EDR","NDR","SIEM","EmailGW","Firewall"]
ASSET_EXPOSURE = ["internal","internet_facing","dmz"]
IP_REPUTATION = ["good","unknown","suspicious","bad"]
USER_ROLES = ["standard","admin","service_account"]
DOWNTIME = ["low","medium","high"]
COUNTRIES = ["US","ES","FR","DE","GB","IN","BR","INTERNAL"]

def rand_bool(p_true=0.5):
    return 1 if random.random() < p_true else 0

def gen_ip(private=True):
    if private:
        return f"10.{random.randint(0,255)}.{random.randint(0,255)}.{random.randint(1,254)}"
    return f"{random.randint(1,223)}.{random.randint(0,255)}.{random.randint(0,255)}.{random.randint(1,254)}"


# --- Distribuciones "realistas" (igual que el dataset) ---

PHASE_WEIGHTS = {
    "reconnaissance": 38,
    "initial_access": 35,
    "execution": 16,
    "lateral_movement": 9,
    "exfiltration": 2,
}

VALID_COMBINATIONS = {
    "reconnaissance": {
        "alert_types": ["port_scan", "brute_force_attempt", "phishing_email"],
        "alert_type_weights": [78, 18, 4],
        "asset_types": ["server", "database", "cloud_service"],
        "asset_type_weights": [45, 40, 15],
        "severity_weights": [70, 20, 7, 2, 1],  # severidad 1..5
    },
    "initial_access": {
        "alert_types": ["phishing_email", "suspicious_login", "brute_force_attempt", "malware_detected"],
        "alert_type_weights": [35, 25, 25, 15],
        "asset_types": ["workstation", "server", "cloud_service"],
        "asset_type_weights": [60, 25, 15],
        "severity_weights": [12, 22, 28, 23, 15],
    },
    "execution": {
        "alert_types": [
            "malware_detected",
            "ransomware_activity",
            "command_and_control",
            "suspicious_login",
            "credential_dump_detected",
            "data_exfiltration",
        ],
        "alert_type_weights": [34, 14, 32, 8, 6, 6],
        "asset_types": ["workstation", "server", "database", "cloud_service"],
        "asset_type_weights": [30, 50, 15, 5],
        "severity_weights": [5, 10, 18, 30, 37],
    },
    "lateral_movement": {
        "alert_types": [
            "credential_dump_detected",
            "privilege_escalation",
            "command_and_control",
            "suspicious_login",
            "ransomware_activity",
        ],
        "alert_type_weights": [28, 23, 33, 8, 8],
        "asset_types": ["server", "database", "workstation"],
        "asset_type_weights": [55, 35, 10],
        "severity_weights": [4, 8, 18, 30, 40],
    },
    "exfiltration": {
        "alert_types": ["data_exfiltration", "command_and_control"],
        "alert_type_weights": [90, 10],
        "asset_types": ["database", "server", "cloud_service"],
        "asset_type_weights": [55, 30, 15],
        "severity_weights": [0, 4, 12, 28, 56],
    },
}

SEVERITY_VALUES = [1, 2, 3, 4, 5]

def weighted_choice(mapping: dict):
    keys = list(mapping.keys())
    weights = list(mapping.values())
    return random.choices(keys, weights=weights, k=1)[0]

def generate_alert():
    ts = datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")

    # 1) Fase con pesos
    attack_phase = weighted_choice(PHASE_WEIGHTS)

    # 2) Según fase, muestrea tipo/activo/severidad con sus pesos
    rules = VALID_COMBINATIONS[attack_phase]

    alert_type = random.choices(
        rules["alert_types"],
        weights=rules["alert_type_weights"],
        k=1
    )[0]

    asset_type = random.choices(
        rules["asset_types"],
        weights=rules["asset_type_weights"],
        k=1
    )[0]

    severity = random.choices(
        SEVERITY_VALUES,
        weights=rules["severity_weights"],
        k=1
    )[0]

    asset_criticality = random.choices(ASSET_CRIT, weights=[55, 30, 15], k=1)[0]

    is_bh = rand_bool(0.6)
    detection_source = random.choice(DETECTION_SOURCES)
    confidence = round(random.uniform(0.55, 0.95), 2)

    src_ip_private = rand_bool(0.7)
    src_ip = gen_ip(private=bool(src_ip_private))

    asset_exposure = random.choice(ASSET_EXPOSURE)
    src_country = "INTERNAL" if src_ip_private else random.choice(COUNTRIES)

    geo_anomaly = rand_bool(0.15)
    ip_rep = random.choice(IP_REPUTATION)
    repeat_offender = rand_bool(0.25)
    prev_30d = random.randint(0, 8) if repeat_offender else random.randint(0, 3)

    time_window_minutes = random.choice([1, 5, 15, 30, 60, 120, 240])

    # event_count: más alto en reconnaissance
    if attack_phase == "reconnaissance":
        event_count = random.randint(80, 250)
    else:
        event_count = random.randint(5, 60)

    user_role = random.choice(USER_ROLES)
    is_priv = 1 if user_role in ["admin", "service_account"] and rand_bool(0.5) else 0

    isolation_supported = rand_bool(0.8)
    downtime_tolerance = random.choice(DOWNTIME)

    return {
        "alert_type": alert_type,
        "attack_phase": attack_phase,
        "asset_type": asset_type,
        "asset_criticality": asset_criticality,
        "severity": int(severity),
        "timestamp_utc": ts,
        "is_business_hours": int(is_bh),
        "detection_source": detection_source,
        "confidence": float(confidence),
        "src_ip": src_ip,
        "asset_exposure": asset_exposure,
        "src_country": src_country,
        "geo_anomaly": int(geo_anomaly),
        "ip_reputation": ip_rep,
        "repeat_offender": int(repeat_offender),
        "previous_incidents_30d": int(prev_30d),
        "event_count": int(event_count),
        "time_window_minutes": int(time_window_minutes),
        "user_role": user_role,
        "is_privileged_account": int(is_priv),
        "isolation_supported": int(isolation_supported),
        "downtime_tolerance": downtime_tolerance
    }

def pg_conn():
    return psycopg2.connect(
        host=PG_HOST, port=PG_PORT, dbname=PG_DB, user=PG_USER, password=PG_PASS
    )

def insert_alert(payload: dict) -> int:
    """
    Inserta en alerts y crea workflow NEW.
    Devuelve alert_id.
    """
    # Convertimos 0/1 a boolean para columnas boolean en Postgres
    is_business_hours = bool(payload["is_business_hours"])
    geo_anomaly = bool(payload["geo_anomaly"])
    repeat_offender = bool(payload["repeat_offender"])
    is_privileged_account = bool(payload["is_privileged_account"])
    isolation_supported = bool(payload["isolation_supported"])

    with pg_conn() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                WITH ins AS (
                  INSERT INTO alerts(
                    source_system,
                    alert_type, attack_phase, asset_type, asset_criticality,
                    severity, timestamp_utc, is_business_hours,
                    detection_source, confidence,
                    src_ip, asset_exposure, src_country, geo_anomaly,
                    ip_reputation, repeat_offender, previous_incidents_30d,
                    event_count, time_window_minutes,
                    user_role, is_privileged_account,
                    isolation_supported, downtime_tolerance,
                    raw_payload
                  )
                  VALUES (
                    %s,
                    %s,%s,%s,%s,
                    %s,%s,%s,
                    %s,%s,
                    %s,%s,%s,%s,
                    %s,%s,%s,
                    %s,%s,
                    %s,%s,
                    %s,%s,
                    %s::jsonb
                  )
                  RETURNING alert_id
                )
                INSERT INTO alert_workflow(alert_id, status, execution_status)
                SELECT alert_id, 'NEW', 'NOT_RUN' FROM ins
                RETURNING alert_id;
                """,
                (
                    "simulator",
                    payload["alert_type"], payload["attack_phase"], payload["asset_type"], payload["asset_criticality"],
                    int(payload["severity"]), payload["timestamp_utc"], is_business_hours,
                    payload["detection_source"], float(payload["confidence"]),
                    payload["src_ip"], payload["asset_exposure"], payload["src_country"], geo_anomaly,
                    payload["ip_reputation"], repeat_offender, int(payload["previous_incidents_30d"]),
                    int(payload["event_count"]), int(payload["time_window_minutes"]),
                    payload["user_role"], is_privileged_account,
                    isolation_supported, payload["downtime_tolerance"],
                    json.dumps(payload)
                )
            )
            alert_id = cur.fetchone()[0]

            # Log evento
            cur.execute(
                """
                INSERT INTO alert_events(alert_id, event_type, actor, details)
                VALUES (%s, 'ALERT_CREATED', 'simulator-api', %s::jsonb)
                """,
                (alert_id, json.dumps({"note": "Alert inserted by simulator", "payload": payload}))
            )
            return int(alert_id)

def notify_n8n(alert_id: int):
    """
    Notifica a n8n para que arranque workflow.
    """
    resp = requests.post(N8N_WEBHOOK_URL, json={"alert_id": alert_id}, timeout=5)
    resp.raise_for_status()
    return resp.json() if resp.headers.get("content-type","").startswith("application/json") else {"status": "ok"}

class GenerateRequest(BaseModel):
    n: int = 1
    notify: bool = True

@app.get("/health")
def health():
    return {"status": "ok"}

@app.post("/generate")
def generate(req: GenerateRequest):
    if req.n < 1 or req.n > 100:
        raise HTTPException(status_code=400, detail="n debe estar entre 1 y 100")

    created = []
    notify_errors = []

    for _ in range(req.n):
        payload = generate_alert()
        alert_id = insert_alert(payload)
        created.append({"alert_id": alert_id, "payload": payload})

        if req.notify:
            try:
                notify_n8n(alert_id)
            except Exception as e:
                # Importante: aunque falle el webhook, la alerta queda en BD como NEW.
                notify_errors.append({"alert_id": alert_id, "error": str(e)})

    return {
        "created_count": len(created),
        "created_ids": [c["alert_id"] for c in created],
        "notify_enabled": req.notify,
        "notify_errors": notify_errors
    }
