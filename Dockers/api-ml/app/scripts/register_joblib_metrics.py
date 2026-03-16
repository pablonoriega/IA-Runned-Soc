#!/usr/bin/env python3
"""
Register a .joblib model in DB + compute metrics/confusion/importance and store them.

Usage examples:

  # 1) Registrar el modelo base usando baseline csv (recomendado)
        set PG_HOST=localhost&& set PG_PORT=5432&& set PG_DB=socdb&& set PG_USER=soc&& set PG_PASS=socpass&& set PYTHONPATH=%cd%&& python -m app.scripts.register_joblib_metrics --joblib soc_action_recommender_rf.joblib --version v1.0.0-base --dataset train\soc_dataset.csv --artifact-path soc_action_recommender_rf.joblib --set-active
"""

import argparse
from datetime import datetime
from pathlib import Path

import joblib
import numpy as np
import pandas as pd

from sklearn.model_selection import train_test_split
from sklearn.metrics import confusion_matrix, classification_report, accuracy_score
from sklearn.inspection import permutation_importance

from app.trainer import ModelTrainer, TrainerConfig, TARGET, DROP_COLS
from app.model_registry import upsert_model, set_active_model, insert_model_metrics, insert_feature_importance


def _load_dataset(path: str) -> pd.DataFrame:
    p = Path(path)
    if not p.exists():
        raise FileNotFoundError(f"Dataset no existe: {p}")
    if p.suffix.lower() == ".csv":
        return pd.read_csv(p)
    raise ValueError("Dataset debe ser .csv (por ahora)")


def _infer_classes_from_model(model):
    try:
        rf = model.named_steps.get("rf")
        if rf is not None and hasattr(rf, "classes_"):
            return [str(c) for c in rf.classes_]
    except Exception:
        pass
    return None


def main():
    ap = argparse.ArgumentParser(description="Register .joblib model metrics in DB")
    ap.add_argument("--joblib", required=True, help="Ruta al .joblib del modelo")
    ap.add_argument("--version", required=True, help="Version/id a guardar en ia_model.version")
    ap.add_argument("--dataset", required=True, help="CSV dataset para evaluar (ej /app/train/soc_dataset.csv)")
    ap.add_argument("--test-size", type=float, default=0.2, help="Tamaño de test (default 0.2)")
    ap.add_argument("--seed", type=int, default=42, help="random_state (default 42)")
    ap.add_argument("--split", default="test", help="Etiqueta split (train|val|test|cv). Default: test")
    ap.add_argument("--notes", default=None, help="Notas a guardar en ia_model_metrics.notes")
    ap.add_argument("--dataset-ref", default=None, help="dataset_ref a guardar (si no, usa --dataset)")
    ap.add_argument("--artifact-path", default=None, help="Ruta a guardar en ia_model.artifact_path")
    ap.add_argument("--set-active", action="store_true", help="Si se indica, marca este modelo como activo en BD")
    ap.add_argument("--no-importance", action="store_true", help="Si se indica, NO calcula permutation importance")
    args = ap.parse_args()

    joblib_path = Path(args.joblib)
    if not joblib_path.exists():
        raise FileNotFoundError(f"No existe joblib: {joblib_path}")

    # 1) cargar modelo
    model = joblib.load(joblib_path)

    # 2) cargar dataset
    df = _load_dataset(args.dataset)

    # 3) usar trainer para feature engineering y limpieza
    trainer = ModelTrainer(TrainerConfig())

    df = trainer.feature_engineering(df)

    if TARGET not in df.columns:
        raise ValueError(f"El dataset debe tener columna label '{TARGET}' para evaluar.")

    # y
    y_all = df[TARGET].copy()

    # X: eliminar leakage/cardinalidad/ids como en el training
    X_all = df.drop(columns=[c for c in DROP_COLS if c in df.columns]).copy()
    X_all = trainer.strip_training_artifacts(X_all)

    if len(X_all) < 50:
        raise ValueError("Muy pocos datos para evaluar (X_all < 50).")

    # 4) split estratificado
    X_train, X_test, y_train, y_test = train_test_split(
        X_all,
        y_all,
        test_size=args.test_size,
        random_state=args.seed,
        stratify=y_all,
    )

    # 5) predicciones
    y_pred = model.predict(X_test)
    acc = float(accuracy_score(y_test, y_pred))

    # 6) clases y matriz de confusión consistente
    classes = _infer_classes_from_model(model)
    # confusion_matrix necesita labels en el mismo orden para alinear headers
    if classes:
        cm = confusion_matrix(y_test, y_pred, labels=classes)
    else:
        cm = confusion_matrix(y_test, y_pred)

    confusion = {"matrix": cm.tolist()}
    if cm.shape == (2, 2):
        tn, fp, fn, tp = cm.ravel()
        confusion.update({"tn": int(tn), "fp": int(fp), "fn": int(fn), "tp": int(tp)})

    report = classification_report(y_test, y_pred, output_dict=True, zero_division=0)

    metrics_out = {
        "accuracy": float(report.get("accuracy", acc)),
        "macro_avg": report.get("macro avg", {}),
        "weighted_avg": report.get("weighted avg", {}),
        "per_class": {k: v for k, v in report.items() if k not in ("accuracy", "macro avg", "weighted avg")},
        "train_info": {
            "base_rows": int(len(df)),
            "human_rows": 0,
            "base_weight": None,
            "human_weight": None,
            "classes": classes or [],
        },
    }

    # 7) guardar en ia_model
    started_at = datetime.utcnow()
    finished_at = datetime.utcnow()

    upsert_model(
        version=args.version,
        status="DONE",
        artifact_path=args.artifact_path or str(joblib_path),
        scheduled_for=None,
        requested_by="system",
        started_at=started_at,
        finished_at=finished_at,
        error=None,
    )

    # opcional: marcar activo
    if args.set_active:
        set_active_model(args.version)

    # 8) insertar metrics/confusion
    insert_model_metrics(
        version=args.version,
        split=args.split,
        threshold=None,
        metrics=metrics_out,
        confusion=confusion,
        dataset_ref=args.dataset_ref or args.dataset,
        notes=args.notes,
    )

    # 9) permutation importance (opcional)
    if not args.no_importance:
        try:
            perm = permutation_importance(
                model,
                X_test,
                y_test,
                n_repeats=5,
                random_state=args.seed,
                n_jobs=1,
            )
            feats = list(X_test.columns)
            rows_imp = [{"feature": f, "importance": float(v)} for f, v in zip(feats, perm.importances_mean)]
            rows_imp.sort(key=lambda d: d["importance"], reverse=True)

            insert_feature_importance(
                version=args.version,
                method="PERMUTATION",
                importance=rows_imp[:25],
                sample_info={"rows": int(len(X_test)), "n_repeats": 5, "test_size": args.test_size},
            )
        except Exception as e:
            print(f"[WARN] permutation importance falló: {repr(e)}")

    print("[OK] Registrado en BDD:")
    print(f"  version: {args.version}")
    print(f"  joblib: {joblib_path}")
    print(f"  dataset: {args.dataset}")
    print(f"  accuracy: {acc:.4f}")
    if args.set_active:
        print("  ACTIVE: true")


if __name__ == "__main__":
    main()