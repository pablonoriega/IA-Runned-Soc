# %%
# ==================================================
# NOTEBOOK: Entrenamiento del modelo (RandomForest)
# Objetivo: predecir recommended_action a partir del contexto de la alerta
# ==================================================

# -----------------------------
# 0) Imports
# -----------------------------
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import ipaddress
import joblib

from sklearn.model_selection import train_test_split
from sklearn.compose import ColumnTransformer
from sklearn.preprocessing import OneHotEncoder
from sklearn.pipeline import Pipeline
from sklearn.metrics import (
    classification_report,
    confusion_matrix,
    ConfusionMatrixDisplay,
    accuracy_score,
)

from sklearn.ensemble import RandomForestClassifier

# %%
# ==================================================
# 1) Cargar dataset
# ==================================================
# Decisión: el dataset ya contiene una alarma detectada por otro departamento.
# Aquí NO hacemos detección, solo "recomendación de acción".
df = pd.read_csv("soc_dataset.csv")

print("Shape:", df.shape)
print("Columnas:", df.columns.tolist())
df.head()

# %%
# ==================================================
# 2) Exploración rápida
# ==================================================
# Decisión: antes de entrenar, verificamos distribución del target:
# - Si hay desbalance extremo, afectará métricas y aprendizaje.
target = "recommended_action"

counts = df[target].value_counts()
print("Distribución de clases:\n", counts)

plt.figure(figsize=(10, 5))
plt.bar(counts.index, counts.values)
plt.title("Distribución de clases (recommended_action)")
plt.xlabel("Clase")
plt.ylabel("Número de registros")
plt.xticks(rotation=30, ha="right")
plt.tight_layout()
plt.show()

# %%
# ==================================================
# 3) Feature engineering (sin leakage)
# ==================================================
# Decisiones clave:
# (A) NO usar recommended_action_reason:
#     Es una explicación derivada de la decisión final -> fuga de información (leakage).
# (B) NO usar src_ip como string categórico:
#     Alta cardinalidad (miles de IPs) -> sobreajuste y poco valor generalizable.
#     En su lugar derivamos una señal simple: si la IP es privada.
# (C) timestamp_utc:
#     En vez de usar el string completo, extraemos variables robustas: hour/dayofweek.
# (D) event_rate:
#     event_count depende de la ventana temporal. Normalizamos creando "eventos por minuto".

# --- Timestamp ---
df["timestamp_utc_parsed"] = pd.to_datetime(df["timestamp_utc"], errors="coerce", utc=True)
df["hour_utc"] = df["timestamp_utc_parsed"].dt.hour
df["dayofweek_utc"] = df["timestamp_utc_parsed"].dt.dayofweek  # 0=Lunes ... 6=Domingo

# --- IP: privada/pública ---
def is_private_ip(ip_str: str):
    try:
        return int(ipaddress.ip_address(ip_str).is_private)
    except Exception:
        return np.nan

df["src_ip_is_private"] = df["src_ip"].apply(is_private_ip)

# --- event_rate: eventos por minuto ---
df["event_rate"] = df["event_count"] / df["time_window_minutes"].replace(0, np.nan)
df = df.dropna(subset=["event_rate", "src_ip_is_private", "hour_utc", "dayofweek_utc"]).reset_index(drop=True)

# %%
# ==================================================
# 4) Selección de features y target
# ==================================================
TARGET = "recommended_action"

# Columnas excluidas por leakage o cardinalidad alta:
DROP_COLS = [
    TARGET,
    "recommended_action_reason",  # leakage
    "timestamp_utc",              # string original
    "timestamp_utc_parsed",       # intermedia
    "src_ip",                     # cardinalidad alta
]

X = df.drop(columns=[c for c in DROP_COLS if c in df.columns]).copy()
y = df[TARGET].copy()

print("Nº features:", X.shape[1])
print("Features usadas:\n", X.columns.tolist())
print("Clases:\n", sorted(y.unique()))

# %%
# ==================================================
# 5) Split Train/Test (estratificado)
# ==================================================
# Decisión: usamos stratify=y para mantener la misma proporción de clases en train/test.
# Esto es importante en clasificación multiclase con clases minoritarias.
X_train, X_test, y_train, y_test = train_test_split(
    X, y,
    test_size=0.2,
    random_state=42,
    stratify=y
)

print("Train:", X_train.shape, "Test:", X_test.shape)
print("Distribución (train):\n", y_train.value_counts(normalize=True).round(3))

# %%
# ==================================================
# 6) Preprocesado: OneHot + passthrough
# ==================================================
# Decisión: RandomForest en sklearn requiere variables numéricas.
# Para categóricas usamos OneHotEncoder (handle_unknown='ignore') para:
# - no fallar si aparece una categoría nueva en producción.
categorical_features = X.select_dtypes(include=["object"]).columns.tolist() # Extrae las columnas de texto
numeric_features = [c for c in X.columns if c not in categorical_features]

print("Categóricas:", categorical_features)
print("Numéricas:", numeric_features)

preprocess = ColumnTransformer(
    transformers=[
        ("cat", OneHotEncoder(handle_unknown="ignore"), categorical_features),
        ("num", "passthrough", numeric_features),
    ],
    remainder="drop"
)

# %%
# ==================================================
# 7) Modelo: RandomForestClassifier
# ==================================================
# - Baseline fuerte en datos tabulares
# - Captura no linealidades e interacciones (fase+severidad+criticidad+contexto)
# - Robusto y con poca ingeniería extra
# - Permite obtener importancias de variables (interpretabilidad parcial)
#
# class_weight='balanced_subsample':
# - ayuda a que cada árbol vea un balance más equilibrado por clase.

rf = RandomForestClassifier(
    n_estimators=400,
    random_state=42,
    n_jobs=-1,
    class_weight="balanced_subsample"
)

model = Pipeline(steps=[
    ("preprocess", preprocess),
    ("rf", rf),
])

# Entrenamiento
model.fit(X_train, y_train)

# %%
# ==================================================
# 8) Evaluación del modelo
# ==================================================
y_pred = model.predict(X_test)

print("\n=== RandomForest: resultados ===")
print("Accuracy:", round(accuracy_score(y_test, y_pred), 4))
print("\nClassification report (por clase):")
print(classification_report(y_test, y_pred, digits=3))

# --- Matriz de confusión (conteos) ---
labels = model.named_steps["rf"].classes_
cm = confusion_matrix(y_test, y_pred, labels=labels)

fig, ax = plt.subplots(figsize=(10, 8))
ConfusionMatrixDisplay(cm, display_labels=labels).plot(ax=ax, values_format="d", xticks_rotation=45)
ax.set_title("Matriz de confusión (conteos)")
plt.tight_layout()
plt.show()

# --- Matriz de confusión normalizada ---
# Decisión: normalizamos por fila (clase real) para interpretar RECALL por clase:
# - cada fila suma ~1.0, fácil ver qué clases se confunden.
cm_norm = confusion_matrix(y_test, y_pred, labels=labels, normalize="true")

fig, ax = plt.subplots(figsize=(10, 8))
ConfusionMatrixDisplay(cm_norm, display_labels=labels).plot(ax=ax, values_format=".2f", xticks_rotation=45)
ax.set_title("Matriz de confusión (normalizada por clase real)")
plt.tight_layout()
plt.show()

# %%
# ==================================================
# 9) Importancias del modelo (Top 25)
# ==================================================
# Interpretación:
# - Importancias altas indican variables que el bosque usa mucho para separar clases.
# - En un dataset SOC es normal ver severity, phase, criticidad, event_count/event_rate en posiciones altas.

ohe = model.named_steps["preprocess"].named_transformers_["cat"]
cat_feature_names = ohe.get_feature_names_out(categorical_features)

all_feature_names = np.concatenate([cat_feature_names, np.array(numeric_features)])
importances = model.named_steps["rf"].feature_importances_

imp_df = pd.DataFrame({"feature": all_feature_names, "importance": importances})
imp_df = imp_df.sort_values("importance", ascending=False)

imp_df.head(25)

plt.figure(figsize=(10, 6))
topk = imp_df.head(25).iloc[::-1]
plt.barh(topk["feature"], topk["importance"])
plt.title("Imposrtancia de las features (RandomForest)")
plt.xlabel("Importancia")
plt.ylabel("Feature")
plt.tight_layout()
plt.show()

# %%
# ==================================================
# 10) Guardar el modelo (para usarlo en demo / despliegue)
# ==================================================
# Decisión: guardamos el Pipeline completo (preprocesado + modelo),
# lo cual evita errores en producción por preprocesado inconsistente.
joblib.dump(model, "soc_action_recommender_rf.joblib")
print("Modelo guardado en: soc_action_recommender_rf.joblib")

# %%
# ==================================================
# 11) Ejemplo de inferencia (predicción + top-3 probabilidades)
# ==================================================
# Esto es útil para "demostrar" funcionamiento del recomendador en el TFM.
sample = X_test.iloc[[0]].copy()
print("Entrada ejemplo:")

pred = model.predict(sample)[0]
proba = model.predict_proba(sample)[0]
classes = model.named_steps["rf"].classes_

top_idx = np.argsort(proba)[::-1][:3]

print("\nPredicción final:", pred)
print("Top-3 probabilidades:")
for i in top_idx:
    print(f"  {classes[i]}: {proba[i]:.3f}")
