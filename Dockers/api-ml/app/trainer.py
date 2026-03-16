# app/trainer.py
from __future__ import annotations

import os
import shutil
import ipaddress
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Optional, Tuple, Dict, Any

import joblib
import numpy as np
import pandas as pd

from sklearn.model_selection import train_test_split
from sklearn.compose import ColumnTransformer
from sklearn.preprocessing import OneHotEncoder
from sklearn.pipeline import Pipeline
from sklearn.metrics import accuracy_score, classification_report
from sklearn.ensemble import RandomForestClassifier


TARGET = "recommended_action"

TRAIN_COLUMNS = [
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
    "recommended_action",
]

DROP_COLS = [
    TARGET,
    "recommended_action_reason",
    "timestamp_utc",
    "timestamp_utc_parsed",
    "src_ip",
    "alert_id",
]


@dataclass(frozen=True)
class TrainerConfig:
    app_root: Path = Path("/app")
    baseline_path: Path = Path("/app/train/soc_dataset.csv")
    retrain_root: Path = Path("/app/retrain")
    models_root: Path = Path("/app/models")

    human_weight: float = float(os.getenv("HUMAN_WEIGHT", "10.0"))
    base_weight: float = float(os.getenv("BASE_WEIGHT", "1.0"))

    n_estimators: int = 400
    random_state: int = 42


class ModelTrainer:
    """
    - Mantiene dataset  (snapshots + accumulated)
    - Entrena modelo ponderando
    - Gestiona active/inactive
    """

    def __init__(self, cfg: Optional[TrainerConfig] = None):
        self.cfg = cfg or TrainerConfig()

        self.snapshots_dir = self.cfg.retrain_root / "snapshots"
        self.accumulated_dir = self.cfg.retrain_root / "accumulated"
        self.active_dir = self.cfg.models_root / "active"
        self.inactive_dir = self.cfg.models_root / "inactive"

        self.snapshots_dir.mkdir(parents=True, exist_ok=True)
        self.accumulated_dir.mkdir(parents=True, exist_ok=True)
        self.active_dir.mkdir(parents=True, exist_ok=True)
        self.inactive_dir.mkdir(parents=True, exist_ok=True)

    # -------- Dataset management --------

    def normalize_training_df(self, df: pd.DataFrame) -> pd.DataFrame:
        if df is None or df.empty:
            return pd.DataFrame(columns=(["alert_id"] + TRAIN_COLUMNS))

        has_alert_id = "alert_id" in df.columns

        keep = (["alert_id"] if has_alert_id else []) + [c for c in TRAIN_COLUMNS if c in df.columns]
        df = df[keep].copy()

        for c in TRAIN_COLUMNS:
            if c not in df.columns:
                df[c] = pd.NA

        if has_alert_id:
            df = df[["alert_id"] + TRAIN_COLUMNS]
        else:
            df = df[TRAIN_COLUMNS]

        return df

    def deduplicate(self, df: pd.DataFrame) -> pd.DataFrame:
        if df is None or df.empty:
            return df
        if "alert_id" in df.columns:
            return df.drop_duplicates(subset=["alert_id"], keep="last").reset_index(drop=True)
        return df.drop_duplicates(keep="last").reset_index(drop=True)

    def update_human_datasets(self, df_new: pd.DataFrame, version: str, scope_name: str) -> Dict[str, Any]:
        df_new = self.normalize_training_df(df_new)

        if TARGET in df_new.columns:
            df_new = df_new.dropna(subset=[TARGET]).reset_index(drop=True)

        snapshot_path = self.snapshots_dir / f"dataset_{version}_{scope_name}.csv"
        df_new.to_csv(snapshot_path, index=False)

        accumulated_path = self.accumulated_dir / f"training_{scope_name}.csv"

        if accumulated_path.exists():
            df_old = pd.read_csv(accumulated_path)
            df_old = self.normalize_training_df(df_old)
            df_all = pd.concat([df_old, df_new], ignore_index=True)
        else:
            df_all = df_new.copy()

        df_all = self.deduplicate(df_all)
        df_all.to_csv(accumulated_path, index=False)

        return {
            "rows_new": int(len(df_new)),
            "rows_total_accumulated": int(len(df_all)),
            "snapshot_path": str(snapshot_path),
            "accumulated_path": str(accumulated_path),
        }

    # -------- Training pipeline --------

    @staticmethod
    def _is_private_ip(ip_str: str):
        try:
            return int(ipaddress.ip_address(ip_str).is_private)
        except Exception:
            return np.nan

    def feature_engineering(self, df: pd.DataFrame) -> pd.DataFrame:
        df = df.copy()
        df["timestamp_utc_parsed"] = pd.to_datetime(df["timestamp_utc"], errors="coerce", utc=True)
        df["hour_utc"] = df["timestamp_utc_parsed"].dt.hour
        df["dayofweek_utc"] = df["timestamp_utc_parsed"].dt.dayofweek
        df["src_ip_is_private"] = df["src_ip"].apply(self._is_private_ip)
        df["event_rate"] = df["event_count"] / df["time_window_minutes"].replace(0, np.nan)

        df = df.dropna(subset=["event_rate", "src_ip_is_private", "hour_utc", "dayofweek_utc"]).reset_index(drop=True)
        return df

    def strip_training_artifacts(self, df: pd.DataFrame) -> pd.DataFrame:
        df = df.copy()
        if "alert_id" in df.columns:
            df = df.drop(columns=["alert_id"])
        return df

    def build_pipeline(self, X: pd.DataFrame) -> Pipeline:
        categorical_features = X.select_dtypes(include=["object"]).columns.tolist()
        numeric_features = [c for c in X.columns if c not in categorical_features]

        preprocess = ColumnTransformer(
            transformers=[
                ("cat", OneHotEncoder(handle_unknown="ignore"), categorical_features),
                ("num", "passthrough", numeric_features),
            ],
            remainder="drop",
        )

        rf = RandomForestClassifier(
            n_estimators=self.cfg.n_estimators,
            random_state=self.cfg.random_state,
            n_jobs=-1,
            class_weight="balanced_subsample",
        )

        return Pipeline(steps=[("preprocess", preprocess), ("rf", rf)])

    def train_weighted(
        self, df_base: pd.DataFrame, df_human: pd.DataFrame
    ) -> Tuple[Pipeline, Dict[str, Any], Dict[str, Any]]:
        """
        Entrena usando sample_weight:
        - base_weight para filas baseline
        - human_weight para filas humanas

        Devuelve:
          (model, metrics, eval_pack)
        donde eval_pack incluye:
          X_eval, y_eval, y_pred, y_proba (si existe)
        """
        df_base = self.feature_engineering(df_base)
        df_human = self.feature_engineering(df_human)

        y_base = df_base[TARGET].copy()
        y_human = df_human[TARGET].copy()

        X_base = df_base.drop(columns=[c for c in DROP_COLS if c in df_base.columns]).copy()
        X_human = df_human.drop(columns=[c for c in DROP_COLS if c in df_human.columns]).copy()

        X_base = self.strip_training_artifacts(X_base)
        X_human = self.strip_training_artifacts(X_human)

        X_all = pd.concat([X_base, X_human], ignore_index=True)
        y_all = pd.concat([y_base, y_human], ignore_index=True)
        w_all = np.concatenate(
            [
                np.full(len(X_base), self.cfg.base_weight, dtype=float),
                np.full(len(X_human), self.cfg.human_weight, dtype=float),
            ]
        )

        if len(X_all) < 50:
            raise ValueError("Muy pocos datos para entrenar (X_all < 50).")

        X_train, X_test, y_train, y_test, w_train, _w_test = train_test_split(
            X_all,
            y_all,
            w_all,
            test_size=0.2,
            random_state=self.cfg.random_state,
            stratify=y_all,
        )

        model = self.build_pipeline(X_train)
        model.fit(X_train, y_train, rf__sample_weight=w_train)

        y_pred = model.predict(X_test)

        y_proba = None
        # si existe predict_proba, lo guardamos para futuros AUCs / topK offline, etc.
        try:
            y_proba = model.predict_proba(X_test)
        except Exception:
            y_proba = None

        acc = float(accuracy_score(y_test, y_pred))
        report = classification_report(y_test, y_pred, digits=3, output_dict=True, zero_division=0)

        metrics = {
            "accuracy": acc,
            "base_rows": int(len(df_base)),
            "human_rows": int(len(df_human)),
            "base_weight": float(self.cfg.base_weight),
            "human_weight": float(self.cfg.human_weight),
            "classes": [str(c) for c in model.named_steps["rf"].classes_],
            "report": report,
        }

        eval_pack = {
            "X_eval": X_test,  # DataFrame con columnas originales pre-encoding
            "y_eval": y_test,
            "y_pred": y_pred,
            "y_proba": y_proba,
        }

        return model, metrics, eval_pack

    # -------- Model files: active/inactive --------

    def rotate_active_to_inactive(self) -> None:
        for p in self.active_dir.glob("*.joblib"):
            dest = self.inactive_dir / p.name
            if dest.exists():
                ts = datetime.utcnow().strftime("%Y%m%dT%H%M%SZ")
                dest = self.inactive_dir / f"{p.stem}_{ts}.joblib"
            shutil.move(str(p), str(dest))

    def save_active_model(self, model: Pipeline, version: str) -> Path:
        filename = f"soc_action_recommender_{version}.joblib"
        out = self.active_dir / filename
        joblib.dump(model, out)
        return out

    def load_active_model_if_any(self) -> Optional[Pipeline]:
        models = list(self.active_dir.glob("*.joblib"))
        if not models:
            return None
        models.sort(key=lambda p: p.stat().st_mtime, reverse=True)
        return joblib.load(models[0])