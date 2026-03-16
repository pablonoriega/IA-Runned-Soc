# %%
# ==================================================
# Imports
# ==================================================
import pandas as pd
import matplotlib.pyplot as plt

# (opcional) usar seaborn si está disponible
try:
    import seaborn as sns
    sns.set(style="whitegrid")
    USE_SNS = True
except Exception:
    USE_SNS = False

plt.rcParams["figure.figsize"] = (11, 6)


# %%
# ==================================================
# Cargar dataset principal
# ==================================================
df = pd.read_csv("soc_dataset.csv")

print("Primeras filas del dataset:")
print(df.head())

print("\nColumnas:")
print(df.columns.tolist())

print("\nInformación general del dataset:")
print(df.info())

print("\nValores únicos (resumen) en columnas clave:")
key_cols = [
    "alert_type", "attack_phase", "asset_type", "asset_criticality", "severity",
    "recommended_action", "recommended_action_reason",
    "detection_source", "asset_exposure", "ip_reputation", "user_role",
    "is_business_hours", "geo_anomaly", "repeat_offender", "is_privileged_account",
    "isolation_supported", "downtime_tolerance", "src_country"
]

for c in key_cols:
    if c in df.columns:
        nunique = df[c].nunique(dropna=False)
        print(f"- {c}: {nunique} únicos")

print("\nEstadísticas básicas numéricas:")
num_cols = df.select_dtypes(include="number").columns.tolist()
print(df[num_cols].describe().T.round(3))


# %%
# ==================================================
# Crear dataset de muestra (10%)
# ==================================================
sample_df = df.sample(frac=0.10, random_state=42).reset_index(drop=True)

print("\nTamaño dataset original:", len(df))
print("Tamaño dataset sample (10%):", len(sample_df))


# %%
# ==================================================
# Guardar dataset sample
# ==================================================
sample_out = "soc_dataset_sample.csv"
sample_df.to_csv(sample_out, index=False)

print(f"\nDataset de muestra guardado como: {sample_out}")
