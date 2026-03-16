-- -----------------------------
-- 0) Helpers: trigger updated_at
-- -----------------------------
CREATE OR REPLACE FUNCTION set_updated_at()
RETURNS TRIGGER AS $$
BEGIN
  NEW.updated_at = NOW();
  RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- -----------------------------
-- 1) alerts (tabla principal)
-- -----------------------------
CREATE TABLE IF NOT EXISTS alerts (
  alert_id BIGSERIAL PRIMARY KEY,

  created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),

  -- Origen / integración (simulador, SIEM, etc.)
  source_system TEXT NOT NULL DEFAULT 'simulator',
  external_id TEXT NULL,

  -- Campos del dataset (normalizados)
  alert_type TEXT NOT NULL,
  attack_phase TEXT NOT NULL,
  asset_type TEXT NOT NULL,
  asset_criticality TEXT NOT NULL,

  severity SMALLINT NOT NULL CHECK (severity BETWEEN 1 AND 5),

  -- Momento del evento (UTC)
  timestamp_utc TIMESTAMPTZ NOT NULL,

  is_business_hours BOOLEAN NOT NULL,

  detection_source TEXT NOT NULL,
  confidence DOUBLE PRECISION NOT NULL CHECK (confidence >= 0 AND confidence <= 1),

  src_ip INET NOT NULL,
  asset_exposure TEXT NOT NULL,
  src_country TEXT NOT NULL,
  geo_anomaly BOOLEAN NOT NULL,

  ip_reputation TEXT NOT NULL,
  repeat_offender BOOLEAN NOT NULL,
  previous_incidents_30d INTEGER NOT NULL CHECK (previous_incidents_30d >= 0),

  event_count INTEGER NOT NULL CHECK (event_count >= 1),
  time_window_minutes INTEGER NOT NULL CHECK (time_window_minutes IN (1,5,15,30,60,120,240)),

  user_role TEXT NOT NULL,
  is_privileged_account BOOLEAN NOT NULL,

  isolation_supported BOOLEAN NOT NULL,
  downtime_tolerance TEXT NOT NULL,

  -- JSON original (audit/debug)
  raw_payload JSONB NULL
);

-- Índices útiles (búsquedas SOC)
CREATE INDEX IF NOT EXISTS idx_alerts_timestamp ON alerts(timestamp_utc DESC);
CREATE INDEX IF NOT EXISTS idx_alerts_type_phase ON alerts(alert_type, attack_phase);
CREATE INDEX IF NOT EXISTS idx_alerts_src_ip ON alerts(src_ip);
CREATE INDEX IF NOT EXISTS idx_alerts_asset ON alerts(asset_type, asset_criticality);

-- -----------------------------
-- 2) alert_workflow (estado actual)
-- -----------------------------
CREATE TABLE IF NOT EXISTS alert_workflow (
  alert_id BIGINT PRIMARY KEY REFERENCES alerts(alert_id) ON DELETE CASCADE,

  -- Estado del flujo
  status TEXT NOT NULL DEFAULT 'NEW',

  -- Asignación
  assigned_to TEXT NULL,
  assigned_at TIMESTAMPTZ NULL,

  -- Recomendación ML (estado actual)
  model_version TEXT NULL,
  model_recommended_action TEXT NULL,
  model_confidence DOUBLE PRECISION NULL CHECK (model_confidence >= 0 AND model_confidence <= 1),
  model_top_k JSONB NULL,

  -- Human-in-the-loop
  human_decision TEXT NULL,      -- ACCEPT | REJECT
  human_final_action TEXT NULL,  -- acción final elegida/confirmada
  human_reason TEXT NULL,
  human_decided_by TEXT NULL,
  human_decided_at TIMESTAMPTZ NULL,
  ai_explanation TEXT NULL,      -- explicación del modelo


  -- Resultado/ejecución
  execution_status TEXT NULL,    -- NOT_RUN | RUNNING | SUCCESS | FAILED
  execution_details JSONB NULL,
  processed_at TIMESTAMPTZ NULL,
  closed_at TIMESTAMPTZ NULL,

  -- Auditoría
  updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- Trigger updated_at en workflow
DROP TRIGGER IF EXISTS trg_workflow_set_updated_at ON alert_workflow;
CREATE TRIGGER trg_workflow_set_updated_at
BEFORE UPDATE ON alert_workflow
FOR EACH ROW EXECUTE FUNCTION set_updated_at();

-- Índice clave para n8n (polling por estado)
CREATE INDEX IF NOT EXISTS idx_workflow_status_updated ON alert_workflow(status, updated_at DESC);

-- -----------------------------
-- 3) alert_events (histórico/auditoría)
-- -----------------------------
CREATE TABLE IF NOT EXISTS alert_events (
  event_id BIGSERIAL PRIMARY KEY,
  alert_id BIGINT NOT NULL REFERENCES alerts(alert_id) ON DELETE CASCADE,

  event_time TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  event_type TEXT NOT NULL,
  actor TEXT NULL,
  details JSONB NULL
);

CREATE INDEX IF NOT EXISTS idx_events_alert_time ON alert_events(alert_id, event_time DESC);
CREATE INDEX IF NOT EXISTS idx_events_type_time ON alert_events(event_type, event_time DESC);

-- -----------------------------
-- 4) ia_model (versionado de modelos IA)
-- -----------------------------
CREATE TABLE IF NOT EXISTS ia_model (
  -- versión / id del modelo o job
  version TEXT PRIMARY KEY,

  -- fecha oficial del modelo listo para usar
  date TIMESTAMPTZ NOT NULL DEFAULT NOW(),

  -- estado del entrenamiento
  status TEXT NOT NULL DEFAULT 'DONE',
  -- SCHEDULED | RUNNING | DONE | ERROR

  -- programación
  scheduled_for TIMESTAMPTZ NULL,

  -- auditoría
  requested_by TEXT NULL,
  created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  started_at TIMESTAMPTZ NULL,
  finished_at TIMESTAMPTZ NULL,

  -- errores
  error TEXT NULL,

  -- path del artefacto del modelo
  artifact_path TEXT NULL,
  is_active BOOLEAN NOT NULL DEFAULT FALSE
);

CREATE INDEX idx_ia_model_status_sched
ON ia_model(status, scheduled_for DESC NULLS LAST, created_at DESC);

CREATE INDEX idx_ia_model_date
ON ia_model(date DESC);

INSERT INTO ia_model (
  version,
  date,
  status,
  scheduled_for,
  requested_by,
  created_at,
  started_at,
  finished_at,
  error,
  artifact_path
) VALUES (
  'v1.0.0-base',              -- versión inicial
  NOW(),                      -- fecha oficial del modelo
  'DONE',                     -- ya está listo
  NULL,                       -- no estaba programado
  'system',                   -- creado por sistema
  NOW(),                      -- fecha de creación
  NOW(),                      -- inicio (opcionalmente igual)
  NOW(),                      -- finalización
  NULL,                       -- sin errores
  '/models/v1.0.0-base/model.pkl'  -- path del artefacto
);

-- =========================
-- TRAINING MODE TABLES
-- =========================

CREATE TABLE IF NOT EXISTS training_session (
  session_id BIGSERIAL PRIMARY KEY,
  created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  finished_at TIMESTAMPTZ NULL,

  operator_id TEXT NOT NULL DEFAULT 'unknown',

  -- configuración seleccionada por el operador
  config JSONB NOT NULL,

  status TEXT NOT NULL DEFAULT 'RUNNING',  -- RUNNING | FINISHED | ABORTED
  total_questions INTEGER NOT NULL DEFAULT 0,
  correct_count INTEGER NOT NULL DEFAULT 0,
  wrong_count INTEGER NOT NULL DEFAULT 0,
  score_pct DOUBLE PRECISION NOT NULL DEFAULT 0
);

CREATE INDEX IF NOT EXISTS idx_training_session_operator
ON training_session(operator_id, created_at DESC);

CREATE TABLE IF NOT EXISTS training_item (
  item_id BIGSERIAL PRIMARY KEY,
  session_id BIGINT NOT NULL REFERENCES training_session(session_id) ON DELETE CASCADE,

  created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),

  -- alerta sintética
  alert_payload JSONB NOT NULL,

  -- clave de corrección
  expected_action TEXT NULL,

  status TEXT NOT NULL DEFAULT 'PENDING' -- PENDING | ANSWERED
);

CREATE INDEX IF NOT EXISTS idx_training_item_session_status
ON training_item(session_id, status, item_id);

CREATE TABLE IF NOT EXISTS training_answer (
  answer_id BIGSERIAL PRIMARY KEY,
  item_id BIGINT NOT NULL REFERENCES training_item(item_id) ON DELETE CASCADE,
  session_id BIGINT NOT NULL REFERENCES training_session(session_id) ON DELETE CASCADE,

  answered_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),

  operator_action TEXT NOT NULL,
  operator_reason TEXT NOT NULL,

  -- feedback del sistema (n8n)
  correct_action TEXT NOT NULL,
  is_correct BOOLEAN NOT NULL,
  score DOUBLE PRECISION NOT NULL DEFAULT 0,
  feedback_text TEXT NOT NULL,

  feedback_json JSONB NULL
);

CREATE INDEX IF NOT EXISTS idx_training_answer_session
ON training_answer(session_id, answered_at DESC);


-- =========================
-- IA MODEL METRICS
-- =========================
CREATE TABLE IF NOT EXISTS ia_model_metrics (
  model_version TEXT NOT NULL REFERENCES ia_model(version) ON DELETE CASCADE,

  computed_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  split TEXT NOT NULL DEFAULT 'test', -- train | val | test | cv
  threshold DOUBLE PRECISION NULL,    

  -- métricas "clásicas"
  metrics JSONB NOT NULL,             -- accuracy, precision, recall, f1, auc, pr_auc, etc.
  confusion JSONB NOT NULL,           -- {"tp":..,"fp":..,"tn":..,"fn":..,"matrix":[[tn,fp],[fn,tp]]}

  -- trazabilidad
  dataset_ref TEXT NULL,              -- ej: /retrain/snapshots/dataset_retrain_x.csv o hash
  notes TEXT NULL,

  PRIMARY KEY (model_version, computed_at, split)
);

CREATE INDEX IF NOT EXISTS idx_ia_model_metrics_latest
ON ia_model_metrics(model_version, computed_at DESC);

-- =========================
-- IA MODEL FEATURE IMPORTANCE
-- =========================
CREATE TABLE IF NOT EXISTS ia_model_feature_importance (
  model_version TEXT NOT NULL REFERENCES ia_model(version) ON DELETE CASCADE,

  computed_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  method TEXT NOT NULL, -- SHAP | PERMUTATION | GINI | LIME_SAMPLE

  -- lista ordenada top features (resumen)
  importance JSONB NOT NULL,
  -- ejemplo de formato:
  -- [
  --   {"feature":"severity","importance":0.123},
  --   {"feature":"asset_criticality","importance":0.098}
  -- ]

  sample_info JSONB NULL,  -- ej: {"rows":1000,"strategy":"random","positive_class":"ACCEPT"}

  PRIMARY KEY (model_version, computed_at, method)
);

CREATE INDEX IF NOT EXISTS idx_ia_model_importance_latest
ON ia_model_feature_importance(model_version, computed_at DESC);
