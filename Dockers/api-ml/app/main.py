# app/main.py
from fastapi import FastAPI, HTTPException
import numpy as np
import pandas as pd
import joblib
import ipaddress

from pathlib import Path
from datetime import datetime
from typing import Optional

from sklearn.metrics import confusion_matrix, classification_report
from sklearn.inspection import permutation_importance

from app.models import PredictRequest, RetrainRunRequest
from app.db import get_conn
from app.sql import SELECT_TRAINING_ALL_CLOSED, SELECT_TRAINING_REJECTED_ONLY
from app.trainer import ModelTrainer, TrainerConfig, TARGET

from app.model_registry import (
    upsert_model,
    set_active_model,
    insert_model_metrics,
    insert_feature_importance,
)

MODEL_SEED_PATH = "soc_action_recommender_rf.joblib"

app = FastAPI(title="SOC Action Recommender API", version="1.0")

trainer = ModelTrainer(TrainerConfig())

# Carga modelo al arrancar:
model = trainer.load_active_model_if_any() or joblib.load(MODEL_SEED_PATH)

FEATURE_COLUMNS = [
    "alert_type",
    "attack_phase",
    "asset_type",
    "asset_criticality",
    "severity",
    "is_business_hours",
    "detection_source",
    "confidence",
    "asset_exposure",
    "src_country",
    "geo_anomaly",
    "ip_reputation",
    "repeat_offender",
    "previous_incidents_30d",
    "event_count",
    "time_window_minutes",
    "user_role",
    "is_privileged_account",
    "isolation_supported",
    "downtime_tolerance",
    "hour_utc",
    "dayofweek_utc",
    "src_ip_is_private",
    "event_rate",
]

REQUIRED_RAW_FIELDS = [
    "alert_type",
    "attack_phase",
    "asset_type",
    "asset_criticality",
    "severity",
    "is_business_hours",
    "detection_source",
    "confidence",
    "asset_exposure",
    "src_country",
    "geo_anomaly",
    "ip_reputation",
    "repeat_offender",
    "previous_incidents_30d",
    "event_count",
    "time_window_minutes",
    "user_role",
    "is_privileged_account",
    "isolation_supported",
    "downtime_tolerance",
    "timestamp_utc",
    "src_ip",
]


@app.get("/health")
def health():
    return {"status": "ok"}


def _is_private_ip(ip_str: str) -> int:
    try:
        return int(ipaddress.ip_address(ip_str).is_private)
    except Exception:
        return 0


def build_features(payload: dict) -> pd.DataFrame:
    missing = [k for k in REQUIRED_RAW_FIELDS if k not in payload]
    if missing:
        raise HTTPException(status_code=400, detail=f"Faltan campos en 'data': {missing}")

    ts = pd.to_datetime(payload["timestamp_utc"], errors="coerce", utc=True)
    if pd.isna(ts):
        raise HTTPException(status_code=400, detail="timestamp_utc inválido (no se pudo parsear)")

    hour_utc = int(ts.hour)
    dayofweek_utc = int(ts.dayofweek)

    src_ip_is_private = _is_private_ip(payload["src_ip"])

    try:
        tw = float(payload["time_window_minutes"])
    except Exception:
        raise HTTPException(status_code=400, detail="time_window_minutes debe ser numérico")
    if tw == 0:
        raise HTTPException(status_code=400, detail="time_window_minutes no puede ser 0")

    try:
        ec = float(payload["event_count"])
    except Exception:
        raise HTTPException(status_code=400, detail="event_count debe ser numérico")

    event_rate = ec / tw

    row = dict(payload)
    row["hour_utc"] = hour_utc
    row["dayofweek_utc"] = dayofweek_utc
    row["src_ip_is_private"] = src_ip_is_private
    row["event_rate"] = event_rate

    return pd.DataFrame([[row.get(c) for c in FEATURE_COLUMNS]], columns=FEATURE_COLUMNS)


@app.post("/predict")
def predict(req: PredictRequest):
    top_k = int(req.top_k)
    if top_k < 1 or top_k > 7:
        raise HTTPException(status_code=400, detail="top_k debe estar entre 1 y 7")

    X_one = build_features(req.data)

    pred = model.predict(X_one)[0]
    proba = model.predict_proba(X_one)[0]
    classes = model.named_steps["rf"].classes_

    idx = np.argsort(proba)[::-1]
    top = [{"action": str(classes[i]), "prob": float(proba[i])} for i in idx[:top_k]]

    return {
        "recommended_action": str(pred),
        "confidence": float(np.max(proba)),
        "top_k": top,
    }


def _parse_iso_dt(s: Optional[str]) -> Optional[datetime]:
    if not s:
        return None
    try:
        return datetime.fromisoformat(s.replace("Z", "+00:00"))
    except Exception:
        return None


@app.post("/retrain/run")
def retrain_run(req: RetrainRunRequest):
    global model

    if req.type != "RETRAIN_MODEL":
        raise HTTPException(status_code=400, detail="type inválido")

    dt_sched = _parse_iso_dt(req.scheduled_for)
    if req.scheduled_for and dt_sched is None:
        raise HTTPException(status_code=400, detail="scheduled_for inválido (ISO)")

    scope = (req.dataset or "").strip()
    if scope not in ("rejected_only", "all_closed", ""):
        raise HTTPException(status_code=400, detail="dataset inválido (usa rejected_only|all_closed)")
    scope_name = scope or "all_closed"

    started_at = datetime.utcnow()

    try:
        upsert_model(
            version=req.version,
            status="RUNNING",
            artifact_path=None,
            scheduled_for=dt_sched,
            requested_by="system",
            started_at=started_at,
            finished_at=None,
            error=None,
        )
    except Exception:
        pass

    # 1) Leer dataset  NUEVO desde BDD (y actualizar accumulated)
    query = SELECT_TRAINING_REJECTED_ONLY if scope == "rejected_only" else SELECT_TRAINING_ALL_CLOSED

    with get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute(query)
            rows = cur.fetchall()

    df_new = pd.DataFrame(rows)

    # actualiza retrain/snapshots + retrain/accumulated
    ds_info = trainer.update_human_datasets(df_new=df_new, version=req.version, scope_name=scope_name)

    # 2) Cargar baseline
    baseline_path = trainer.cfg.baseline_path
    if not baseline_path.exists():
        try:
            upsert_model(
                version=req.version,
                status="ERROR",
                artifact_path=None,
                scheduled_for=dt_sched,
                requested_by="system",
                started_at=started_at,
                finished_at=datetime.utcnow(),
                error=f"No existe baseline en {baseline_path}",
            )
        except Exception:
            pass
        raise HTTPException(status_code=500, detail=f"No existe baseline en {baseline_path}. Monta /app/train.")

    df_base = pd.read_csv(baseline_path)

    # 3) Cargar acumulado
    accum_path = Path(ds_info["accumulated_path"])
    df_human = pd.read_csv(accum_path)
    df_human = trainer.normalize_training_df(df_human)

    # Asegura label
    if TARGET in df_human.columns:
        df_human = df_human.dropna(subset=[TARGET]).reset_index(drop=True)
    if len(df_human) == 0:
        try:
            upsert_model(
                version=req.version,
                status="ERROR",
                artifact_path=None,
                scheduled_for=dt_sched,
                requested_by="system",
                started_at=started_at,
                finished_at=datetime.utcnow(),
                error="Dataset humano acumulado vacío tras limpieza.",
            )
        except Exception:
            pass
        raise HTTPException(status_code=422, detail="Dataset humano acumulado vacío tras limpieza.")

    # 4) Entrenar ponderado
    try:
        new_model, train_metrics, eval_pack = trainer.train_weighted(df_base=df_base, df_human=df_human)
    except Exception as e:
        try:
            upsert_model(
                version=req.version,
                status="ERROR",
                artifact_path=None,
                scheduled_for=dt_sched,
                requested_by="system",
                started_at=started_at,
                finished_at=datetime.utcnow(),
                error=repr(e),
            )
        except Exception:
            pass
        raise HTTPException(status_code=500, detail=f"Fallo entrenando: {repr(e)}")

    # 5) Rotate modelos: active -> inactive
    trainer.rotate_active_to_inactive()

    # 6) Guardar nuevo en active
    active_path = trainer.save_active_model(new_model, version=req.version)

    # 7) Activarlo en memoria
    model = new_model

    finished_at = datetime.utcnow()

    # 8) Persistir ia_model DONE + marcar activo en BDD
    try:
        upsert_model(
            version=req.version,
            status="DONE",
            artifact_path=str(active_path),
            scheduled_for=dt_sched,
            requested_by="system",
            started_at=started_at,
            finished_at=finished_at,
            error=None,
        )
        set_active_model(req.version)
    except Exception:
        pass

    # 9) Guardar métricas + confusion en BDD
    try:
        X_eval = eval_pack["X_eval"]
        y_eval = eval_pack["y_eval"]
        y_pred = eval_pack["y_pred"]

        labels = train_metrics.get("classes") or None
        cm = confusion_matrix(y_eval, y_pred, labels=labels) if labels else confusion_matrix(y_eval, y_pred)
        confusion = {"matrix": cm.tolist()}
        if cm.shape == (2, 2):
            tn, fp, fn, tp = cm.ravel()
            confusion.update({"tn": int(tn), "fp": int(fp), "fn": int(fn), "tp": int(tp)})

        report = classification_report(y_eval, y_pred, output_dict=True, zero_division=0)

        metrics_out = {
            "accuracy": float(report.get("accuracy", 0.0)),
            "macro_avg": report.get("macro avg", {}),
            "weighted_avg": report.get("weighted avg", {}),
            "per_class": {k: v for k, v in report.items() if k not in ("accuracy", "macro avg", "weighted avg")},
            "train_info": {
                "base_rows": train_metrics.get("base_rows"),
                "human_rows": train_metrics.get("human_rows"),
                "base_weight": train_metrics.get("base_weight"),
                "human_weight": train_metrics.get("human_weight"),
                "classes": train_metrics.get("classes"),
            },
        }

        insert_model_metrics(
            version=req.version,
            split="test",
            threshold=None,
            metrics=metrics_out,
            confusion=confusion,
            dataset_ref=ds_info.get("snapshot_path") or ds_info.get("accumulated_path"),
            notes=f"scope={scope_name}",
        )
    except Exception:
        pass

    # 10) Feature importance (PERMUTATION) -> BDD
    try:
        X_eval = eval_pack["X_eval"]
        y_eval = eval_pack["y_eval"]

        perm = permutation_importance(
            new_model,
            X_eval,
            y_eval,
            n_repeats=5,
            random_state=42,
            n_jobs=1,
        )

        feats = list(X_eval.columns)
        rows_imp = [{"feature": f, "importance": float(v)} for f, v in zip(feats, perm.importances_mean)]
        rows_imp.sort(key=lambda d: d["importance"], reverse=True)

        insert_feature_importance(
            version=req.version,
            method="PERMUTATION",
            importance=rows_imp[:25],
            sample_info={"rows": int(len(X_eval)), "n_repeats": 5},
        )
    except Exception:
        pass

    return {
        "status": "ok",
        "version": req.version,
        "scheduled_for_parsed": dt_sched.isoformat() if dt_sched else None,
        "scope": scope_name,
        "dataset_update": ds_info,
        "baseline_path": str(baseline_path),
        "active_model_path": str(active_path),
        "inactive_dir": str(trainer.inactive_dir),
        "metrics": {
            "accuracy": train_metrics["accuracy"],
            "base_rows": train_metrics["base_rows"],
            "human_rows": train_metrics["human_rows"],
            "base_weight": train_metrics["base_weight"],
            "human_weight": train_metrics["human_weight"],
            "classes": train_metrics["classes"],
        },
    }