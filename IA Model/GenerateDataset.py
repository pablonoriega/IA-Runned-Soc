# -*- coding: utf-8 -*-
"""
Generador de dataset sintético SOC
==========================================

Este script genera un dataset tabular (CSV) que simula alertas ya detectadas en un SOC y, a partir de ellas,
recomienda una acción de respuesta (label) con una etiqueta explicativa (reason tag) auditable.

Idea principal
--------------
- NO decide si el evento es malicioso: parte de que "ya existe una alerta".
- Sí decide "qué hacer ahora" (recommended_action) usando un playbook base + una capa de políticas
  (contexto, confianza, reputación IP, anomalías, etc.).
- Incluye campos de contexto para evitar un dataset trivial (determinista) y acercarse a escenarios reales.

Salida
------
- soc_dataset.csv en el directorio actual, con N filas (por defecto 50.000).
"""

import random
import pandas as pd
import ipaddress
from datetime import datetime, timedelta, timezone


# ============================================================
# 1) DOMINIOS (catálogos de valores) Y DISTRIBUCIONES
# ============================================================

# Tipos de alerta típicos de un SOC (simplificados pero representativos)
ALERT_TYPES = [
    "malware_detected",
    "ransomware_activity",
    "phishing_email",
    "credential_dump_detected",
    "suspicious_login",
    "brute_force_attempt",
    "port_scan",
    "command_and_control",
    "data_exfiltration",
    "privilege_escalation",
]

# Tipos de activo: condicionan tanto exposición como acciones disponibles
ASSET_TYPES = ["workstation", "server", "database", "cloud_service"]

# Criticidad del activo (impacto al negocio si cae o se ve comprometido)
ASSET_CRITICALITY = ["low", "medium", "high"]

# Fases del ataque (kill chain / MITRE-like). Sirve para coherencia (no todo pasa en cualquier fase).
ATTACK_PHASES = ["reconnaissance", "initial_access", "execution", "lateral_movement", "exfiltration"]

# Severidad ordinal 1-5 (1 = bajo, 5 = crítico)
SEVERITY = [1, 2, 3, 4, 5]

# Pesos de muestreo de fases: en muchos SOC hay MUCHO reconocimiento/acceso inicial
# y menos exfiltración (menos frecuente o menos detectada).
PHASE_WEIGHTS = {
    "reconnaissance": 38,
    "initial_access": 35,
    "execution": 16,
    "lateral_movement": 9,
    "exfiltration": 2,
}

# Pesos de criticidad: típicamente hay muchos activos low/medium y menos high
CRIT_WEIGHTS = [55, 30, 15]  # low > medium > high

# Fuentes de detección: aportan "contexto" (ej. EDR suele ser más directo que SIEM en endpoint).
DETECTION_SOURCES = [
    "EDR", "SIEM", "IDS", "NDR", "Firewall", "WAF", "CloudTrail", "EmailGW", "DLP", "IAM"
]

# VALID_COMBINATIONS garantiza coherencia semántica:
# - Qué tipos de alerta son más probables en cada fase
# - Qué tipos de activo aparecen más por fase
# - Distribución de severidades por fase (recon suele ser más baja que exfil).
VALID_COMBINATIONS = {
    "reconnaissance": {
        "alert_types": ["port_scan", "brute_force_attempt", "phishing_email"],
        "alert_type_weights": [78, 18, 4],
        "asset_types": ["server", "database", "cloud_service"],
        "asset_type_weights": [45, 40, 15],
        "severity_weights": [70, 20, 7, 2, 1],
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


# ============================================================
# 2) HELPERS
# ============================================================
def _weighted_choice(mapping):
    """
    Selecciona una clave del diccionario mapping usando los pesos asociados.
    mapping = {valor: peso, ...}
    """
    keys = list(mapping.keys())
    weights = list(mapping.values())
    return random.choices(keys, weights=weights, k=1)[0]


def _clamp(x, lo=0.0, hi=1.0):
    """Limita x al rango [lo, hi]. Se usa para que la confianza quede en 0..0.99."""
    return max(lo, min(hi, x))


# ============================================================
# 3) PLAYBOOK BASE: decide_action(...)
# ============================================================
def decide_action(alert_type, attack_phase, asset_type, asset_criticality, severity):
    """
    Reglas base (tipo playbook) para recomendar una acción.
    Este bloque es determinista: misma entrada -> misma acción.
    Posteriormente, apply_policy(...) introduce contexto y ajustes realistas.

    Acciones posibles (labels):
    - ignore               : no actuar (ruido)
    - investigate          : investigar/triage
    - block_ip             : bloquear IP/origen
    - reset_credentials    : forzar reset de credenciales (usuario final)
    - disable_account      : deshabilitar cuenta (más contundente)
    - isolate_host         : aislar host (EDR / NAC / red)
    - escalate_incident    : escalar incidente (IR formal, coordinación, etc.)
    """
    # Regla "importante": exfiltración es crítica casi siempre -> escalar
    if attack_phase == "exfiltration":
        return "escalate_incident"

    # ------------------
    # LATERAL MOVEMENT
    # ------------------
    if attack_phase == "lateral_movement":
        # Señal por severidad alta o activo crítico
        if severity >= 4 or asset_criticality == "high":
            return "escalate_incident"

        # Dump de credenciales / escalado: acciones sobre identidad
        if alert_type in ["credential_dump_detected", "privilege_escalation"]:
            if asset_type == "workstation":
                return "reset_credentials"  # típico en endpoint de usuario
            return "disable_account"        # en servidores/infra suele ser más seguro cortar cuenta

        # Criticidad media -> endurecer con disable_account
        if asset_criticality == "medium":
            return "disable_account"

        # En server/db, aislar puede cortar movimiento lateral
        if asset_type in ["server", "database"]:
            return "isolate_host"

        # En cloud, aislar host no siempre existe, se actúa en identidad
        if asset_type == "cloud_service":
            return "disable_account"

        return "investigate"

    # ------------------
    # EXECUTION
    # ------------------
    if attack_phase == "execution":
        # Exfil dentro de ejecución: si es serio -> escalar
        if alert_type == "data_exfiltration":
            if severity >= 3 or asset_criticality in ["medium", "high"]:
                return "escalate_incident"
            return "investigate"

        # Caso especial: base de datos (activo sensible)
        if asset_type == "database":
            if alert_type in ["malware_detected", "ransomware_activity", "command_and_control"]:
                if severity >= 3:
                    # Si el negocio es importante, se escala; si no, aislar puede bastar
                    return "escalate_incident" if asset_criticality in ["medium", "high"] else "isolate_host"
                return "investigate"
            if alert_type in ["suspicious_login", "brute_force_attempt"]:
                # En DB crítica, una autenticación rara se corta antes
                return "disable_account" if asset_criticality in ["medium", "high"] else "investigate"
            return "investigate"

        # Severidad alta general -> aislar o escalar según criticidad
        if severity >= 4:
            if asset_criticality in ["medium", "high"]:
                return "escalate_incident"
            return "isolate_host"

        # Malware/ransom/C2: aislamiento, salvo cloud (donde se actúa en identidad)
        if alert_type in ["ransomware_activity", "malware_detected", "command_and_control"]:
            if asset_type == "cloud_service":
                if severity >= 4 or asset_criticality == "high":
                    return "escalate_incident"
                return "disable_account"
            return "isolate_host"

        # Eventos de autenticación: reset/disable dependiendo del activo
        if alert_type in ["suspicious_login", "brute_force_attempt"]:
            if asset_type == "workstation":
                return "reset_credentials"
            if asset_criticality in ["medium", "high"]:
                return "disable_account"
            return "investigate"

        # Ajuste por criticidad cuando nada anterior se ha aplicado
        if asset_criticality == "high":
            return "isolate_host"
        if asset_criticality == "medium":
            return "disable_account"
        return "investigate"

    # ------------------
    # INITIAL ACCESS
    # ------------------
    if attack_phase == "initial_access":
        # Caso extremo: severidad máxima o activo muy crítico -> escalar
        if severity >= 5 or asset_criticality == "high":
            return "escalate_incident"

        # Alertas típicas de acceso inicial
        if alert_type in ["phishing_email", "suspicious_login", "brute_force_attempt"]:
            # Baja severidad -> investigar (evita falsos positivos destructivos)
            if severity <= 2:
                return "investigate"
            # severidad 3: reset en workstation (cuentas de usuario), en otros investigar
            if severity == 3:
                return "reset_credentials" if asset_type == "workstation" else "investigate"
            # severidad >=4: endurecer (reset o disable)
            if severity >= 4:
                return "reset_credentials" if asset_type == "workstation" else "disable_account"

        # Malware detectado durante acceso inicial: aislar (y escalar si cloud crítico)
        if alert_type == "malware_detected":
            if asset_type == "cloud_service" and asset_criticality in ["medium", "high"]:
                return "escalate_incident"
            return "isolate_host"

        # Criticidad media -> disable por prudencia
        if asset_criticality == "medium":
            return "disable_account"

        return "investigate"

    # ------------------
    # RECONNAISSANCE
    # ------------------
    if attack_phase == "reconnaissance":
        # Port scan: a severidad baja puede ignorarse si activo no crítico (ruido internet)
        if alert_type == "port_scan":
            if severity <= 2:
                return "ignore" if asset_criticality == "low" else "investigate"
            if severity == 3:
                return "investigate"
            return "block_ip"

        # Brute force: a severidad alta puede bloquear IP
        if alert_type == "brute_force_attempt":
            if severity <= 2:
                return "investigate"
            if severity == 3:
                return "disable_account" if asset_criticality in ["medium", "high"] else "investigate"
            return "block_ip"

        # C2 en recon (raro) -> bloquear
        if alert_type == "command_and_control":
            return "block_ip"

        # Resto: regla general por severidad
        if severity <= 2:
            return "ignore"
        if severity == 3:
            return "investigate"
        return "block_ip"

    raise ValueError("Unhandled SOC decision state")


# ============================================================
# 4) GENERACIÓN DE IPs Y TIMESTAMPS
# ============================================================
def gen_public_ip():
    """
    Genera una IP pública en bloques /8 preseleccionados.
    Razón: evita rangos reservados y controla la distribución (realismo).
    """
    blocks = [
        ipaddress.ip_network("8.0.0.0/8"),
        ipaddress.ip_network("31.0.0.0/8"),
        ipaddress.ip_network("45.0.0.0/8"),
        ipaddress.ip_network("66.0.0.0/8"),
        ipaddress.ip_network("80.0.0.0/8"),
        ipaddress.ip_network("104.0.0.0/8"),
        ipaddress.ip_network("142.0.0.0/8"),
        ipaddress.ip_network("151.0.0.0/8"),
        ipaddress.ip_network("185.0.0.0/8"),
        ipaddress.ip_network("195.0.0.0/8"),
    ]
    net = random.choice(blocks)
    ip = net.network_address + random.randint(1, net.num_addresses - 2)
    return str(ipaddress.ip_address(ip))


def gen_private_ip():
    """
    Genera IP privada de RFC1918: 10/8, 172.16/12, 192.168/16.
    Se usa cuando el activo es "internal" (no internet-facing).
    """
    nets = [
        ipaddress.ip_network("10.0.0.0/8"),
        ipaddress.ip_network("192.168.0.0/16"),
        ipaddress.ip_network("172.16.0.0/12"),
    ]
    net = random.choice(nets)
    ip = net.network_address + random.randint(1, net.num_addresses - 2)
    return str(ipaddress.ip_address(ip))


def gen_timestamp_utc(days_back=45):
    """
    Timestamp UTC aleatorio dentro de los últimos N días.
    days_back=45 simula una ventana de observación reciente.
    """
    now = datetime.now(timezone.utc)
    start = now - timedelta(days=days_back)
    ts = start + timedelta(seconds=random.randint(0, int((now - start).total_seconds())))
    return ts


def is_business_hours_utc(ts: datetime):
    """
    Marca si el evento ocurrió en horario laboral (L-V 08:00-18:00) en UTC.
    Importante: aquí se usa UTC de forma consistente; si se quisiera local (Europe/Madrid),
    habría que convertir zona horaria.
    """
    dow = ts.weekday()
    hour = ts.hour
    return int(dow < 5 and 8 <= hour < 18)


# ============================================================
# 5) CONTEXTO ENRIQUECIDO + CONFIDENCE + REPUTACIÓN + ETC.
# ============================================================

# Países para simular origen externo. "INTERNAL" se usa cuando el origen es privado.
COUNTRIES = ["ES", "FR", "DE", "GB", "IT", "NL", "US", "BR", "IN", "CN", "RU", "PL", "UA", "TR", "MX", "AR", "CO", "SE", "NO", "JP"]


def choose_detection_source(alert_type, attack_phase):
    """
    Asigna la fuente de detección de forma coherente con el tipo de alerta.
    Ejemplos:
    - phishing -> EmailGW (más probable)
    - malware/ransom -> EDR
    - port_scan/bruteforce -> IDS/Firewall
    - exfil -> DLP/NDR
    """
    if alert_type == "phishing_email":
        return random.choices(["EmailGW", "SIEM"], weights=[80, 20], k=1)[0]
    if alert_type in ["port_scan", "brute_force_attempt"]:
        return random.choices(["IDS", "Firewall", "SIEM", "NDR"], weights=[35, 35, 20, 10], k=1)[0]
    if alert_type in ["malware_detected", "ransomware_activity"]:
        return random.choices(["EDR", "SIEM", "NDR"], weights=[70, 20, 10], k=1)[0]
    if alert_type in ["credential_dump_detected", "privilege_escalation"]:
        return random.choices(["EDR", "SIEM", "IAM"], weights=[50, 35, 15], k=1)[0]
    if alert_type in ["command_and_control", "data_exfiltration"]:
        return random.choices(["NDR", "DLP", "SIEM", "EDR"], weights=[35, 30, 25, 10], k=1)[0]
    if attack_phase == "exfiltration":
        return random.choices(["DLP", "NDR", "SIEM"], weights=[45, 35, 20], k=1)[0]
    return random.choice(DETECTION_SOURCES)


def enrich_context(attack_phase, alert_type, asset_type, asset_criticality, severity):
    """
    Genera variables de contexto que influyen en políticas (apply_policy) y dan realismo.
    Devuelve un dict con:
    - timestamp_utc, is_business_hours
    - detection_source, confidence
    - src_ip, asset_exposure, src_country, geo_anomaly
    - ip_reputation, repeat_offender, previous_incidents_30d
    - event_count, time_window_minutes
    - user_role, is_privileged_account
    - isolation_supported, downtime_tolerance
    """
    ts = gen_timestamp_utc(days_back=45)
    biz = is_business_hours_utc(ts)

    # ---------- Exposición del activo ----------
    # Workstations suelen ser internas. Servidores y cloud a veces son internet-facing.
    if asset_type == "workstation":
        exposure = random.choices(["internal", "internet_facing"], weights=[97, 3], k=1)[0]
    elif asset_type in ["server", "cloud_service"]:
        exposure = random.choices(["internal", "internet_facing"], weights=[70, 30], k=1)[0]
    else:
        exposure = random.choices(["internal", "internet_facing"], weights=[92, 8], k=1)[0]

    # La IP origen depende de exposición (externa -> pública, interna -> privada)
    src_ip = gen_public_ip() if exposure == "internet_facing" else gen_private_ip()

    # ---------- Geolocalización y anomalía ----------
    # Si es interno, no hay país ni anomalía.
    if exposure == "internal":
        src_country = "INTERNAL"
        geo_anomaly = 0
    else:
        # Distribución ponderada de países (no uniforme).
        src_country = random.choices(
            COUNTRIES,
            weights=[6,5,5,5,5,3,10,4,7,6,5,4,3,3,4,3,3,2,2,4],
            k=1
        )[0]
        # Probabilidad base de anomalía geográfica
        base_geo = 0.10
        # Aumenta en fases donde el atacante suele actuar con credenciales o acceso
        if attack_phase in ["initial_access", "execution"]:
            base_geo += 0.07
        # Aumenta en auth/phishing/dump (indicador de compromiso de cuenta)
        if alert_type in ["suspicious_login", "phishing_email", "credential_dump_detected"]:
            base_geo += 0.10
        geo_anomaly = int(random.random() < base_geo)

    # ---------- Reputación de IP ----------
    # Interno: mayoritariamente "good". Externo: depende de fase y tipo.
    if exposure == "internal":
        rep = random.choices(["good", "suspicious", "bad"], weights=[88, 10, 2], k=1)[0]
    else:
        base = [45, 35, 20]  # good, suspicious, bad
        if attack_phase == "reconnaissance":
            base = [30, 40, 30]
        if alert_type in ["command_and_control", "data_exfiltration"]:
            base = [12, 33, 55]
        if alert_type == "phishing_email":
            base = [25, 45, 30]
        rep = random.choices(["good", "suspicious", "bad"], weights=base, k=1)[0]

    # ---------- Repeat offender + incident history ----------
    # Si la IP es mala, es más probable que sea reincidente y tenga más incidentes previos.
    if rep == "bad":
        repeat_offender = random.choices([0, 1], weights=[50, 50], k=1)[0]
        prev_inc = max(0, int(random.gauss(4, 2)))
    elif rep == "suspicious":
        repeat_offender = random.choices([0, 1], weights=[72, 28], k=1)[0]
        prev_inc = max(0, int(random.gauss(2, 1.5)))
    else:
        repeat_offender = random.choices([0, 1], weights=[92, 8], k=1)[0]
        prev_inc = max(0, int(random.gauss(0.6, 0.9)))
    prev_inc = min(prev_inc, 15)

    # ---------- Rol de usuario ----------
    # Importa para endurecer acciones en cuentas privilegiadas.
    user_role = random.choices(["standard", "admin", "service_account"], weights=[76, 14, 10], k=1)[0]
    is_privileged = int(user_role in ["admin", "service_account"])

    # ---------- ¿Se puede aislar? ----------
    # En endpoints/servidores suele ser posible; en cloud a veces no (o es distinto).
    if asset_type in ["server", "database", "workstation"]:
        isolation_supported = random.choices([0, 1], weights=[8, 92], k=1)[0]
    else:
        isolation_supported = random.choices([0, 1], weights=[45, 55], k=1)[0]

    # ---------- Tolerancia a downtime ----------
    # Activos high suelen tolerar menos downtime (más coste de parada).
    if asset_criticality == "high":
        downtime = random.choices(["low", "medium", "high"], weights=[55, 35, 10], k=1)[0]
    elif asset_criticality == "medium":
        downtime = random.choices(["low", "medium", "high"], weights=[35, 45, 20], k=1)[0]
    else:
        downtime = random.choices(["low", "medium", "high"], weights=[20, 50, 30], k=1)[0]

    # ---------- Correlación: ventana + event_count ----------
    # Simula el "volumen" de eventos que sostienen la alerta.
    if attack_phase == "reconnaissance":
        time_window = random.choices([1, 5, 15, 30], weights=[25, 40, 25, 10], k=1)[0]
        event_count = max(1, int(random.gauss(120, 60)))
    elif attack_phase == "initial_access":
        time_window = random.choices([5, 15, 30, 60], weights=[25, 35, 25, 15], k=1)[0]
        event_count = max(1, int(random.gauss(20, 15)))
    elif attack_phase == "execution":
        time_window = random.choices([5, 15, 30, 60, 120], weights=[15, 25, 25, 20, 15], k=1)[0]
        event_count = max(1, int(random.gauss(35, 25)))
    elif attack_phase == "lateral_movement":
        time_window = random.choices([15, 30, 60, 120], weights=[20, 35, 25, 20], k=1)[0]
        event_count = max(1, int(random.gauss(18, 12)))
    else:
        time_window = random.choices([30, 60, 120, 240], weights=[15, 30, 35, 20], k=1)[0]
        event_count = max(1, int(random.gauss(10, 8)))
    event_count = min(event_count, 500)

    # ---------- Fuente de detección y confianza ----------
    src = choose_detection_source(alert_type, attack_phase)

    # Confianza base y sumas heurísticas para simular mas fiablididad segun reglas.
    conf = random.uniform(0.45, 0.90)
    if src in ["EDR", "DLP", "CloudTrail", "IAM"]:
        conf += 0.06
    if src in ["SIEM"]:
        conf += 0.02
    if attack_phase in ["execution", "lateral_movement", "exfiltration"]:
        conf += 0.05
    if alert_type in ["ransomware_activity", "command_and_control", "credential_dump_detected", "data_exfiltration", "privilege_escalation"]:
        conf += 0.07
    if severity >= 4:
        conf += 0.06
    if geo_anomaly == 1 and alert_type in ["suspicious_login", "phishing_email"]:
        conf += 0.04
    if repeat_offender == 1:
        conf += 0.03

    confidence = round(_clamp(conf, 0.0, 0.99), 2)

    return {
        "timestamp_utc": ts.isoformat().replace("+00:00", "Z"),
        "is_business_hours": biz,
        "detection_source": src,
        "confidence": confidence,
        "src_ip": src_ip,
        "asset_exposure": exposure,
        "src_country": src_country,
        "geo_anomaly": geo_anomaly,
        "ip_reputation": rep,
        "repeat_offender": repeat_offender,
        "previous_incidents_30d": prev_inc,
        "event_count": event_count,
        "time_window_minutes": time_window,
        "user_role": user_role,
        "is_privileged_account": is_privileged,
        "isolation_supported": isolation_supported,
        "downtime_tolerance": downtime,
    }


# ============================================================
# 6) CAPA DE POLÍTICA (apply_policy): añade realismo + reason tag
# ============================================================

# Etiquetas de razón. Se guarda una sola razón principal por fila (explicable y auditable).

REASON_TAGS = [
    "playbook_base",
    "phase_exfiltration",
    "high_severity_or_critical_asset",
    "strong_signal_detected",
    "low_confidence_investigate",
    "bad_ip_reputation",
    "repeat_offender",
    "internet_facing_recon",
    "privileged_account_risk",
    "geo_anomaly_auth",
    "isolation_not_supported",
    "downtime_constraint",
    "human_variation",
]

def apply_policy(action, attack_phase, alert_type, asset_type, asset_criticality, severity, ctx):
    """
    Ajusta la acción base con "políticas" que dependen del contexto.
    Devuelve (final_action, reason_tag).

    Filosofía:
    - El playbook base decide una acción razonable con info mínima.
    - La policy layer evita acciones destructivas con baja confianza,
      endurece cuando hay señales fuertes (mala reputación, privilegiado, geo-anomaly),
      y respeta restricciones operativas (downtime, aislamiento no soportado).
    """
    # 0) Exfiltration manda siempre (regla de negocio)
    if attack_phase == "exfiltration":
        return "escalate_incident", "phase_exfiltration"

    # 1) Baja confianza: no bloquear/aislar/deshabilitar si no es crítico y severidad moderada
    if ctx["confidence"] < 0.60 and action in ["block_ip", "disable_account", "isolate_host"]:
        if severity <= 3 and asset_criticality != "high":
            return "investigate", "low_confidence_investigate"

    # 2) Reputación IP mala: si severidad >= 3, endurece (bloqueo o disable_account)
    if ctx["ip_reputation"] == "bad" and severity >= 3:
        if action in ["ignore", "investigate"]:
            new_action = "block_ip" if attack_phase == "reconnaissance" else "disable_account"
            return new_action, "bad_ip_reputation"

    # 3) Repeat offender: reincidente + correlación alta
    if ctx["repeat_offender"] == 1:
        if action == "ignore":
            return "investigate", "repeat_offender"

        # Recon con mucha actividad en poco tiempo -> bloquear
        if attack_phase == "reconnaissance" and ctx["event_count"] >= 80 and ctx["time_window_minutes"] <= 15:
            return "block_ip", "repeat_offender"

        # Si iba a investigar y severidad >=3, endurecer
        if action == "investigate" and severity >= 3:
            new_action = "block_ip" if attack_phase == "reconnaissance" else "disable_account"
            return new_action, "repeat_offender"

    # 4) Internet-facing recon: es más razonable bloquear si severidad >=3
    if attack_phase == "reconnaissance" and ctx["asset_exposure"] == "internet_facing":
        if alert_type in ["port_scan", "brute_force_attempt"] and severity >= 3:
            return "block_ip", "internet_facing_recon"

    # 5) Cuentas privilegiadas: riesgo mayor en auth/privilegio
    if ctx["is_privileged_account"] == 1 and alert_type in ["suspicious_login", "brute_force_attempt", "credential_dump_detected", "privilege_escalation"]:
        if severity >= 4 and asset_criticality in ["medium", "high"]:
            return "escalate_incident", "privileged_account_risk"
        if severity >= 3 and action in ["ignore", "investigate", "reset_credentials"]:
            return "disable_account", "privileged_account_risk"

    # 6) Geo anomaly: endurecer en auth/phishing con severidad >=3
    if ctx["geo_anomaly"] == 1 and alert_type in ["suspicious_login", "phishing_email"]:
        if severity >= 3 and action in ["investigate", "ignore"]:
            new_action = "reset_credentials" if asset_type == "workstation" else "disable_account"
            return new_action, "geo_anomaly_auth"

    # 7) Si la acción era aislar pero no es posible, sustituir por opciones
    if action == "isolate_host" and ctx["isolation_supported"] == 0:
        if severity >= 4 or asset_criticality in ["medium", "high"]:
            return "escalate_incident", "isolation_not_supported"
        return "disable_account", "isolation_not_supported"

    # 8) Downtime bajo: evitar aislar salvo extremo
    if ctx["downtime_tolerance"] == "low" and action == "isolate_host" and severity < 5:
        new_action = "escalate_incident" if asset_criticality == "high" else "disable_account"
        return new_action, "downtime_constraint"

    # 9) Señales fuertes (C2/ransom/exfil) en fases avanzadas -> escalar si severidad/criticidad altas
    if alert_type in ["command_and_control", "ransomware_activity", "data_exfiltration"]:
        if attack_phase in ["execution", "lateral_movement"] and (severity >= 4 or asset_criticality in ["medium", "high"]):
            return "escalate_incident", "strong_signal_detected"

    # 10) Severidad 5 + criticidad alta => escalar casi siempre
    if severity == 5 and asset_criticality == "high":
        return "escalate_incident", "high_severity_or_critical_asset"

    # 11) Variación humana (ruido realista): pequeños overrides en casos no críticos
    if asset_criticality != "high" and severity <= 3 and action in ["block_ip", "disable_account"]:
        if random.random() < 0.03:
            return "investigate", "human_variation"

    # Si nada se aplica, se mantiene acción del playbook base
    return action, "playbook_base"


# ============================================================
# 7) MUESTREO DE UN REGISTRO COMPLETO
# ============================================================
def sample_record():
    """
    Genera una fila completa:
    1) Muestra fase según PHASE_WEIGHTS
    2) Muestra alert_type/asset_type/severity según VALID_COMBINATIONS de esa fase
    3) Muestra criticidad con CRIT_WEIGHTS
    4) Enriquecer contexto (enrich_context)
    5) Calcular acción base (decide_action)
    6) Ajustar por política (apply_policy) y guardar reason tag
    """
    phase = _weighted_choice(PHASE_WEIGHTS)
    rules = VALID_COMBINATIONS[phase]

    alert_type = random.choices(
        rules["alert_types"],
        weights=rules.get("alert_type_weights"),
        k=1
    )[0]

    asset_type = random.choices(
        rules["asset_types"],
        weights=rules.get("asset_type_weights"),
        k=1
    )[0]

    asset_criticality = random.choices(
        ASSET_CRITICALITY,
        weights=CRIT_WEIGHTS,
        k=1
    )[0]

    severity = random.choices(
        SEVERITY,
        weights=rules["severity_weights"],
        k=1
    )[0]

    ctx = enrich_context(phase, alert_type, asset_type, asset_criticality, severity)

    base_action = decide_action(alert_type, phase, asset_type, asset_criticality, severity)
    final_action, reason = apply_policy(base_action, phase, alert_type, asset_type, asset_criticality, severity, ctx)

    return {
        "alert_type": alert_type,
        "attack_phase": phase,
        "asset_type": asset_type,
        "asset_criticality": asset_criticality,
        "severity": severity,
        **ctx,
        "recommended_action": final_action,
        "recommended_action_reason": reason,
    }


# ============================================================
# 8) RECORTE RESPETANDO MÍNIMOS POR CLASE (balance controlado)
# ============================================================
def _trim_respecting_mins(df, total_rows, min_per_action, seed):
    """
    Si durante el "oversampling" se generan filas extra para cumplir mínimos por acción,
    esta función recorta el dataframe a total_rows garantizando:
    - conservar al menos min_per_action[action] filas (si existen)
    - completar el resto con muestreo aleatorio del remanente
    """
    if len(df) <= total_rows or not min_per_action:
        return df

    protected_parts = []
    for action, m in min_per_action.items():
        if m <= 0:
            continue
        sub = df[df["recommended_action"] == action]
        take = min(m, len(sub))
        if take > 0:
            protected_parts.append(sub.sample(n=take, random_state=seed))

    protected = pd.concat(protected_parts, ignore_index=True) if protected_parts else df.iloc[0:0].copy()
    remaining = df.drop(index=protected.index, errors="ignore")

    need = total_rows - len(protected)
    if need <= 0:
        return protected.sample(n=total_rows, random_state=seed).reset_index(drop=True)

    if len(remaining) <= need:
        out = pd.concat([protected, remaining], ignore_index=True)
        return out.sample(frac=1, random_state=seed).reset_index(drop=True)

    out = pd.concat([protected, remaining.sample(n=need, random_state=seed)], ignore_index=True)
    return out.sample(frac=1, random_state=seed).reset_index(drop=True)


# ============================================================
# 9) FUNCIÓN PRINCIPAL DE GENERACIÓN
# ============================================================
def generate_soc_dataset_realistic(
    total_rows=50000,
    seed=42,
    min_per_action=None,
    max_extra=300000
):
    """
    Genera el dataset completo.

    Parámetros:
    - total_rows: tamaño final del dataset
    - seed: semilla de random (reproducibilidad)
    - min_per_action: dict {acción: mínimo deseado} para evitar clases demasiado pequeñas
    - max_extra: límite de iteraciones extra para no quedar en bucle si una clase es difícil de obtener

    Procedimiento:
    1) Genera total_rows filas con sample_record()
    2) Si se exigen mínimos por acción:
        - calcula cuántas faltan
        - genera filas extra (hasta max_extra intentos) que cumplan esa acción
        - concatena y recorta manteniendo mínimos
    3) Mezcla filas (shuffle) y devuelve dataframe final
    """
    random.seed(seed)

    records = [sample_record() for _ in range(total_rows)]
    df = pd.DataFrame(records)

    if min_per_action:
        counts = df["recommended_action"].value_counts().to_dict()
        extra = []

        for action, target_min in min_per_action.items():
            current = counts.get(action, 0)
            missing = max(0, target_min - current)

            it = 0
            while missing > 0 and it < max_extra:
                r = sample_record()
                if r["recommended_action"] == action:
                    extra.append(r)
                    missing -= 1
                it += 1

            if missing > 0:
                print(f"[WARN] No se alcanzó el mínimo para '{action}': faltan {missing}")

        if extra:
            df = pd.concat([df, pd.DataFrame(extra)], ignore_index=True)

        df = _trim_respecting_mins(df, total_rows, min_per_action, seed)

    # Shuffle final para evitar bloques de clases
    return df.sample(frac=1, random_state=seed).reset_index(drop=True)


# ============================================================
# 10) MAIN: ejecución como script
# ============================================================
if __name__ == "__main__":
    # Se solicita un dataset de 50k filas con mínimos por acción para evitar clases raras.
    df = generate_soc_dataset_realistic(
        total_rows=50000,
        seed=42,
        min_per_action={
            "ignore": 2500,
            "investigate": 9000,
            "block_ip": 8500,
            "reset_credentials": 1800,
            "disable_account": 2500,
            "isolate_host": 2000,
            "escalate_incident": 700,
        }
    )

    # Salidas de diagnóstico: distribución de fases, acciones, reason tags, estadística de confidence
    print("Tamaño:", len(df))
    print("\nDistribución por fase:")
    print(df["attack_phase"].value_counts(normalize=True).round(3))
    print("\nDistribución por acción:")
    print(df["recommended_action"].value_counts())
    print("\nDistribución reason tags (top 12):")
    print(df["recommended_action_reason"].value_counts().head(12))
    print("\nConfidence (resumen):")
    print(df["confidence"].describe().round(3))

    # Exportación a CSV
    out = "soc_dataset.csv"
    df.to_csv(out, index=False)
    print(f"\nDataset generado: {out}")
