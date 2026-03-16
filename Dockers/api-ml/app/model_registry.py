# app/model_registry.py
import json
from datetime import datetime
from typing import Any, Dict, List, Optional

from app.db import get_conn


def upsert_model(
    *,
    version: str,
    status: str,
    artifact_path: Optional[str],
    scheduled_for: Optional[datetime] = None,
    requested_by: str = "system",
    started_at: Optional[datetime] = None,
    finished_at: Optional[datetime] = None,
    error: Optional[str] = None,
) -> None:
    """
    Inserta/actualiza ia_model para esa version.
    NO toca is_active (eso se gestiona en set_active_model()).
    """
    q = """
    INSERT INTO ia_model (
      version, date, status, scheduled_for, requested_by,
      created_at, started_at, finished_at, error, artifact_path, is_active
    )
    VALUES (
      %s, NOW(), %s, %s, %s,
      NOW(), %s, %s, %s, %s, FALSE
    )
    ON CONFLICT (version) DO UPDATE SET
      date = NOW(),
      status = EXCLUDED.status,
      scheduled_for = COALESCE(EXCLUDED.scheduled_for, ia_model.scheduled_for),
      requested_by = COALESCE(EXCLUDED.requested_by, ia_model.requested_by),
      started_at = COALESCE(EXCLUDED.started_at, ia_model.started_at),
      finished_at = COALESCE(EXCLUDED.finished_at, ia_model.finished_at),
      error = EXCLUDED.error,
      artifact_path = COALESCE(EXCLUDED.artifact_path, ia_model.artifact_path);
    """
    with get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute(
                q,
                (
                    version,
                    status,
                    scheduled_for,
                    requested_by,
                    started_at,
                    finished_at,
                    error,
                    artifact_path,
                ),
            )
        conn.commit()


def set_active_model(version: str) -> None:
    """
    Marca este version como activo y desactiva el resto.
    Requiere ia_model.is_active.
    """
    q1 = "UPDATE ia_model SET is_active = FALSE WHERE is_active = TRUE;"
    q2 = "UPDATE ia_model SET is_active = TRUE WHERE version = %s;"
    with get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute(q1)
            cur.execute(q2, (version,))
        conn.commit()


def insert_model_metrics(
    *,
    version: str,
    split: str,
    threshold: Optional[float],
    metrics: Dict[str, Any],
    confusion: Dict[str, Any],
    dataset_ref: Optional[str],
    notes: Optional[str],
) -> None:
    q = """
    INSERT INTO ia_model_metrics (model_version, split, threshold, metrics, confusion, dataset_ref, notes)
    VALUES (%s, %s, %s, %s::jsonb, %s::jsonb, %s, %s);
    """
    with get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute(
                q,
                (
                    version,
                    split,
                    threshold,
                    json.dumps(metrics),
                    json.dumps(confusion),
                    dataset_ref,
                    notes,
                ),
            )
        conn.commit()


def insert_feature_importance(
    *,
    version: str,
    method: str,
    importance: List[Dict[str, Any]],
    sample_info: Optional[Dict[str, Any]] = None,
) -> None:
    q = """
    INSERT INTO ia_model_feature_importance (model_version, method, importance, sample_info)
    VALUES (%s, %s, %s::jsonb, %s::jsonb);
    """
    with get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute(
                q,
                (
                    version,
                    method,
                    json.dumps(importance),
                    json.dumps(sample_info or {}),
                ),
            )
        conn.commit()