# %%
# ==================================================
# Imports
# ==================================================
import pandas as pd
import matplotlib.pyplot as plt

# (opcional)
try:
    import seaborn as sns
    sns.set(style="whitegrid")
    USE_SNS = True
except Exception:
    USE_SNS = False

plt.rcParams["figure.figsize"] = (11, 6)

# %%
# ==================================================
# Cargar dataset
# ==================================================
#df = pd.read_csv("soc_dataset.csv")
df = pd.read_csv("soc_dataset_sample.csv")

print("Primeras filas del dataset:")
print(df.head())

print("\nColumnas:")
print(df.columns.tolist())

print("\nInformación general del dataset:")
print(df.info())

print("\nValores únicos (resumen) en columnas clave:")
key_cols = [
    "alert_type","attack_phase","asset_type","asset_criticality","severity",
    "recommended_action","recommended_action_reason",
    "detection_source","asset_exposure","ip_reputation","user_role",
    "is_business_hours","geo_anomaly","repeat_offender","is_privileged_account",
    "isolation_supported","downtime_tolerance","src_country"
]
for c in key_cols:
    if c in df.columns:
        nunique = df[c].nunique(dropna=False)
        print(f"- {c}: {nunique} únicos")

print("\nEstadísticas básicas numéricas (incluye severity/confidence/event_count/etc):")
num_cols = df.select_dtypes(include="number").columns.tolist()
print(df[num_cols].describe().T.round(3))

# %%
# ==================================================
# Paletas de colores por variable
# ==================================================
ACTION_PALETTE = {
    "ignore": "#95a5a6",
    "investigate": "#3498db",
    "block_ip": "#9b59b6",
    "reset_credentials": "#1abc9c",
    "disable_account": "#f39c12",
    "isolate_host": "#e67e22",
    "escalate_incident": "#e74c3c",
}

PHASE_PALETTE = {
    "reconnaissance": "#2980b9",
    "initial_access": "#16a085",
    "execution": "#f39c12",
    "lateral_movement": "#d35400",
    "exfiltration": "#c0392b",
}

CRIT_PALETTE = {
    "low": "#2ecc71",
    "medium": "#f1c40f",
    "high": "#e74c3c",
}

REP_PALETTE = {
    "good": "#2ecc71",
    "suspicious": "#f1c40f",
    "bad": "#e74c3c",
}

EXPOSURE_PALETTE = {
    "internal": "#3498db",
    "internet_facing": "#e74c3c",
}

# %%
# ==================================================
# Helper para plots de barras (count) con colores
# ==================================================
def plot_count(col, order=None, top=None, title=None, rotate=0, palette=None):
    s = df[col].value_counts(dropna=False)
    if top:
        s = s.head(top)

    if order is not None:
        s = s.reindex(order).dropna()

    colors = None
    if palette is not None:
        # asigna un color por categoría (si existe)
        colors = [palette.get(idx, "#7f8c8d") for idx in s.index]

    ax = s.plot(kind="barh" if rotate == -1 else "bar", color=colors, rot=0 if rotate == -1 else rotate)
    ax.set_title(title or f"Distribución: {col}")
    ax.set_xlabel("Cantidad")
    ax.set_ylabel(col)

    plt.tight_layout()
    plt.show()

# %%
# ==================================================
# Distribución de acciones recomendadas + razones
# ==================================================
print("\nDistribución de acciones recomendadas:")
print(df["recommended_action"].value_counts())

if USE_SNS:
    plt.figure()
    sns.countplot(
        y="recommended_action",
        data=df,
        order=df["recommended_action"].value_counts().index,
        palette=ACTION_PALETTE
    )
    plt.title("Distribución de acciones recomendadas")
    plt.xlabel("Cantidad")
    plt.ylabel("Acción")
    plt.tight_layout()
    plt.show()
else:
    plot_count("recommended_action", title="Distribución de acciones recomendadas", palette=ACTION_PALETTE, rotate=-1)

print("\nTop reasons (motivos) de recomendación:")
print(df["recommended_action_reason"].value_counts().head(15))

if USE_SNS:
    plt.figure()
    sns.countplot(
        y="recommended_action_reason",
        data=df,
        order=df["recommended_action_reason"].value_counts().head(15).index,
        palette="Spectral"
    )
    plt.title("Top 15 motivos de recomendación (recommended_action_reason)")
    plt.xlabel("Cantidad")
    plt.ylabel("Reason tag")
    plt.tight_layout()
    plt.show()
else:
    plot_count("recommended_action_reason", top=15, title="Top 15 motivos de recomendación", rotate=-1)

# %%
# ==================================================
# Distribución por fases y tipos base
# ==================================================
for col in ["attack_phase", "alert_type", "asset_type", "asset_criticality", "severity"]:
    if col == "asset_criticality":
        order = ["low", "medium", "high"]
        palette = CRIT_PALETTE
    elif col == "attack_phase":
        order = ["reconnaissance", "initial_access", "execution", "lateral_movement", "exfiltration"]
        palette = PHASE_PALETTE
    elif col == "severity":
        order = [1, 2, 3, 4, 5]
        palette = "Blues"
    else:
        order = None
        palette = "viridis"

    if USE_SNS:
        plt.figure()
        if col in ["alert_type"]:
            sns.countplot(
                y=col,
                data=df,
                order=df[col].value_counts().index,
                palette="coolwarm"
            )
            plt.ylabel(col)
            plt.xlabel("Cantidad")
        else:
            sns.countplot(
                x=col,
                data=df,
                order=order if order else df[col].value_counts().index,
                palette=palette
            )
            plt.xlabel(col)
            plt.ylabel("Cantidad")

        plt.title(f"Distribución de {col}")
        plt.tight_layout()
        plt.show()
    else:
        plot_count(col, order=order, title=f"Distribución de {col}", rotate=45 if col in ["attack_phase","asset_type"] else 0)

# %%
# ==================================================
# Contexto operativo: distribuciones categóricas
# ==================================================
context_cats = [
    ("detection_source", "Set2", None),
    ("asset_exposure", EXPOSURE_PALETTE, None),
    ("ip_reputation", REP_PALETTE, None),
    ("user_role", "Pastel1", None),
    ("downtime_tolerance", "Set3", ["low", "medium", "high"]),
    ("src_country", "tab20", None),
]

for col, pal, order in context_cats:
    if col not in df.columns:
        continue

    print(f"\nDistribución de {col} (top 15 si aplica):")
    print(df[col].value_counts().head(15))

    if USE_SNS:
        plt.figure()
        plot_order = df[col].value_counts().head(15).index if df[col].nunique() > 15 else df[col].value_counts().index
        if order:
            plot_order = order

        if df[col].nunique() > 10 and col != "downtime_tolerance":
            sns.countplot(y=col, data=df, order=plot_order, palette=pal)
            plt.ylabel(col)
            plt.xlabel("Cantidad")
        else:
            sns.countplot(x=col, data=df, order=plot_order, palette=pal)
            plt.xlabel(col)
            plt.ylabel("Cantidad")

        plt.title(f"Distribución de {col}")
        plt.tight_layout()
        plt.show()
    else:
        plot_count(col, top=15, title=f"Distribución de {col}", rotate=45)

# %%
# ==================================================
# Columnas binarias (0/1)
# ==================================================
binary_cols = ["is_business_hours", "geo_anomaly", "repeat_offender", "is_privileged_account", "isolation_supported"]
for col in binary_cols:
    if col not in df.columns:
        continue
    print(f"\n{col}:")
    print(df[col].value_counts(normalize=True).round(3))

    if USE_SNS:
        plt.figure()
        sns.countplot(x=col, data=df, palette="Set2")
        plt.title(f"Distribución de {col}")
        plt.xlabel(col)
        plt.ylabel("Cantidad")
        plt.tight_layout()
        plt.show()
    else:
        plot_count(col, title=f"Distribución de {col}")

# %%
# ==================================================
# Distribuciones numéricas clave
# ==================================================
num_focus = [c for c in ["confidence", "event_count", "previous_incidents_30d", "time_window_minutes"] if c in df.columns]
for col in num_focus:
    print(f"\nResumen de {col}:")
    print(df[col].describe().round(3))

    plt.figure()
    plt.hist(df[col].dropna(), bins=30, color="#3498db", edgecolor="black", alpha=0.8)
    plt.title(f"Histograma: {col}")
    plt.xlabel(col)
    plt.ylabel("Frecuencia")
    plt.tight_layout()
    plt.show()

# %%
# ==================================================
# Matrices de combinación (normalizadas)
# ==================================================
def show_crosstab(row, col, normalize="index", top_rows=None, top_cols=None, title=""):
    ct = pd.crosstab(df[row], df[col], normalize=normalize)
    if top_rows:
        ct = ct.loc[df[row].value_counts().head(top_rows).index]
    if top_cols:
        ct = ct[df[col].value_counts().head(top_cols).index]
    print(f"\n{title} (normalize={normalize}):")
    print(ct.round(3))
    return ct

ct = show_crosstab(
    "attack_phase", "recommended_action",
    normalize="index",
    title="P(action | attack_phase): acciones por fase"
)

ct3 = show_crosstab(
    "asset_criticality", "recommended_action",
    normalize="index",
    title="P(action | asset_criticality): acciones por criticidad"
)

ct4 = show_crosstab(
    "recommended_action_reason", "recommended_action",
    normalize="index",
    top_rows=15,
    title="P(action | reason): qué acción suele acompañar a cada reason (top 15 reasons)"
)

# %%
# ==================================================
# Heatmaps (solo seaborn)
# ==================================================
if USE_SNS:
    plt.figure(figsize=(12, 5))
    sns.heatmap(ct, cmap="YlGnBu")
    plt.title("Heatmap P(action | attack_phase)")
    plt.xlabel("recommended_action")
    plt.ylabel("attack_phase")
    plt.tight_layout()
    plt.show()

    plt.figure(figsize=(12, 6))
    sns.heatmap(ct3, annot=True, fmt=".2f", cmap="OrRd")
    plt.title("Heatmap P(action | asset_criticality)")
    plt.xlabel("recommended_action")
    plt.ylabel("asset_criticality")
    plt.tight_layout()
    plt.show()

# %%
# ==================================================
# Boxplots útiles
# ==================================================
if USE_SNS and "confidence" in df.columns:
    plt.figure(figsize=(12, 5))
    sns.boxplot(x="recommended_action", y="confidence", data=df, order=df["recommended_action"].value_counts().index, palette="Set2")
    plt.title("Confidence por acción recomendada")
    plt.xlabel("Acción")
    plt.ylabel("Confidence")
    plt.xticks(rotation=30)
    plt.tight_layout()
    plt.show()

if USE_SNS:
    plt.figure(figsize=(12, 5))
    sns.boxplot(
        x="recommended_action",
        y="severity",
        data=df,
        order=df["recommended_action"].value_counts().index,
        palette="Set3"
    )
    plt.title("Severidad por acción recomendada")
    plt.xlabel("Acción")
    plt.ylabel("Severidad")
    plt.xticks(rotation=30)
    plt.tight_layout()
    plt.show()

if USE_SNS and "event_count" in df.columns:
    plt.figure(figsize=(10, 5))
    sns.boxplot(
        x="attack_phase",
        y="event_count",
        data=df,
        order=df["attack_phase"].value_counts().index,
        palette="magma"
    )
    plt.title("Event count por fase")
    plt.xlabel("Fase")
    plt.ylabel("Event count")
    plt.xticks(rotation=30)
    plt.tight_layout()
    plt.show()

# %%
# ==================================================
# Insights rápidos
# ==================================================
print("\nTop 10 combinaciones (criticidad x fase x acción):")
comb = (
    df.groupby(["asset_criticality", "attack_phase", "recommended_action"])
      .size()
      .reset_index(name="count")
      .sort_values("count", ascending=False)
      .head(10)
)
print(comb)

print("\nTop 10 combinaciones (reason x acción):")
comb2 = (
    df.groupby(["recommended_action_reason", "recommended_action"])
      .size()
      .reset_index(name="count")
      .sort_values("count", ascending=False)
      .head(10)
)
print(comb2)

if "recommended_action_reason" in df.columns:
    print("\n% de registros por reason (para ver cuánto influye la policy):")
    print((df["recommended_action_reason"].value_counts(normalize=True) * 100).round(2))
