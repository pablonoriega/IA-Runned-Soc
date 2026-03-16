LIST_ALERTS_BASE = """
SELECT
  a.alert_id,
  a.created_at::text AS created_at,
  a.timestamp_utc::text AS timestamp_utc,
  a.alert_type,
  a.attack_phase,
  a.asset_type,
  a.asset_criticality,
  a.severity,
  a.src_ip,
  a.ip_reputation,
  a.repeat_offender,

  w.status,
  w.model_recommended_action,
  w.model_confidence,
  w.assigned_to,
  w.assigned_at::text AS assigned_at,
  w.processed_at::text AS processed_at,
  w.closed_at::text AS closed_at,
  w.updated_at::text AS updated_at,

  w.human_decision,
  w.human_decided_by,
  w.human_reason
FROM alerts a
JOIN alert_workflow w ON w.alert_id = a.alert_id
"""

COUNT_ALERTS_BASE = """
SELECT COUNT(*)::int AS total
FROM alerts a
JOIN alert_workflow w ON w.alert_id = a.alert_id
"""

DETAIL_ALERT = """
SELECT
  a.alert_id,
  a.created_at::text AS created_at,
  a.source_system,
  a.alert_type,
  a.attack_phase,
  a.asset_type,
  a.asset_criticality,
  a.severity,
  a.timestamp_utc::text AS timestamp_utc,
  a.is_business_hours,
  a.detection_source,
  a.confidence,
  a.src_ip,
  a.asset_exposure,
  a.src_country,
  a.geo_anomaly,
  a.ip_reputation,
  a.repeat_offender,
  a.previous_incidents_30d,
  a.event_count,
  a.time_window_minutes,
  a.user_role,
  a.is_privileged_account,
  a.isolation_supported,
  a.downtime_tolerance,
  a.raw_payload,

  w.status,
  w.assigned_to,
  w.assigned_at::text AS assigned_at,
  w.model_version,
  w.model_recommended_action,
  w.model_confidence,
  w.model_top_k,
  w.ai_explanation,

  w.human_decision,
  w.human_final_action,
  w.human_reason,
  w.human_decided_by,
  w.human_decided_at::text AS human_decided_at,

  w.execution_status,
  w.execution_details,
  w.processed_at::text AS processed_at,
  w.closed_at::text AS closed_at,
  w.updated_at::text AS updated_at
FROM alerts a
JOIN alert_workflow w ON w.alert_id = a.alert_id
WHERE a.alert_id = %s
"""


LIST_EVENTS = """
SELECT event_id, event_time::text AS event_time, event_type, actor, details
FROM alert_events
WHERE alert_id = %s
ORDER BY event_time ASC
"""

UPDATE_DECISION = """
UPDATE alert_workflow
SET
  status = %s,
  human_decision = %s,
  human_final_action = %s,
  human_reason = %s,
  human_decided_by = %s,
  human_decided_at = NOW(),
  closed_at = NOW(),
  updated_at = NOW()
WHERE alert_id = %s
RETURNING alert_id
"""

INSERT_EVENT = """
INSERT INTO alert_events(alert_id, event_type, actor, details)
VALUES (%s, %s, %s, %s::jsonb)
"""
LIST_OPERATORS = """
SELECT
  o.operator_id,
  o.username,
  o.display_name,
  o.email,
  o.role,
  o.is_active,
  o.max_active,
  o.timezone,
  o.shift_name,
  o.on_call,
  o.sla_ack_seconds,
  o.sla_resolve_seconds,
  o.business_hours_only,
  o.skills,
  o.created_at::text AS created_at,
  o.updated_at::text AS updated_at,
  COALESCE(c.active_assigned, 0)::int AS active_assigned
FROM operators o
LEFT JOIN (
  SELECT
    CASE
      WHEN assigned_to ~ '^[0-9]+$' THEN assigned_to::bigint
      ELSE NULL
    END AS operator_id,
    COUNT(*)::int AS active_assigned
  FROM alert_workflow
  WHERE assigned_to IS NOT NULL
    AND status IN ('NEW','PREDICTED','PENDING_HUMAN','IN_PROGRESS')
  GROUP BY 1
) c ON c.operator_id = o.operator_id
WHERE o.is_active = %s
ORDER BY COALESCE(c.active_assigned, 0) ASC, o.operator_id ASC
"""

GET_OPERATOR = """
SELECT
  operator_id,
  username,
  display_name,
  email,
  role,
  is_active,
  max_active,
  timezone,
  shift_name,
  on_call,
  sla_ack_seconds,
  sla_resolve_seconds,
  business_hours_only,
  skills,
  created_at::text AS created_at,
  updated_at::text AS updated_at
FROM operators
WHERE operator_id = %s
"""
# --- SLA por operador (CLOSED) ---

COUNT_OPERATOR_CLOSED = """
SELECT COUNT(*)::int AS total
FROM alert_workflow w
WHERE w.status = 'CLOSED'
  AND w.assigned_to = %s
  AND w.assigned_at IS NOT NULL
  AND w.closed_at IS NOT NULL
"""

LIST_OPERATOR_CLOSED = """
SELECT
  a.alert_id,
  w.assigned_to,
  w.assigned_at::text AS assigned_at,
  w.closed_at::text AS closed_at,
  EXTRACT(EPOCH FROM (w.closed_at - w.assigned_at))::int AS resolve_seconds
FROM alerts a
JOIN alert_workflow w ON w.alert_id = a.alert_id
WHERE w.status = 'CLOSED'
  AND w.assigned_to = %s
  AND w.assigned_at IS NOT NULL
  AND w.closed_at IS NOT NULL
ORDER BY w.closed_at DESC NULLS LAST, a.alert_id DESC
LIMIT %s OFFSET %s
"""

SOC_METRICS_ACK = """
SELECT
  EXTRACT(EPOCH FROM (w.assigned_at - a.created_at))::int AS ack_seconds
FROM alerts a
JOIN alert_workflow w ON w.alert_id = a.alert_id
JOIN operators o ON (
  CASE WHEN w.assigned_to ~ '^[0-9]+$' THEN w.assigned_to::bigint ELSE NULL END
) = o.operator_id
WHERE o.is_active = TRUE
  AND w.assigned_at IS NOT NULL
  AND a.created_at IS NOT NULL
  AND a.created_at >= NOW() - (%s::int * INTERVAL '1 day')
"""

SOC_METRICS_RESOLVE = """
SELECT
  EXTRACT(EPOCH FROM (w.closed_at - w.assigned_at))::int AS resolve_seconds
FROM alert_workflow w
JOIN operators o ON (
  CASE WHEN w.assigned_to ~ '^[0-9]+$' THEN w.assigned_to::bigint ELSE NULL END
) = o.operator_id
WHERE o.is_active = TRUE
  AND w.closed_at IS NOT NULL
  AND w.assigned_at IS NOT NULL
  AND w.closed_at >= NOW() - (%s::int * INTERVAL '1 day')
"""

GET_LATEST_MODEL = """
SELECT version, date::text AS date
FROM ia_model
ORDER BY date DESC
LIMIT 1
"""

INSERT_RETRAIN = """
INSERT INTO ia_model (version, status, scheduled_for, requested_by, created_at)
VALUES (%s, 'SCHEDULED', %s, %s, NOW())
"""

UPDATE_ALL_CLOSED_RETRAIN = """
UPDATE alert_workflow
SET
    execution_status = %s
WHERE
  status = 'CLOSED'
  AND execution_status = 'NOT_RUN';
"""

UPDATE_REJECTED_ONLY_RETRAIN = """
UPDATE alert_workflow
SET
  execution_status = %s
WHERE
  status = 'CLOSED'
  AND execution_status = 'NOT_RUN'
  AND human_decision = %s;
"""

# =========================
# TRAINING SQL
# =========================

TRAINING_LIST_SESSIONS = """
SELECT
  session_id,
  created_at::text AS created_at,
  finished_at::text AS finished_at,
  operator_id,
  status,
  total_questions,
  correct_count,
  wrong_count,
  score_pct
FROM training_session
WHERE operator_id = %s
ORDER BY created_at DESC
LIMIT %s
"""

TRAINING_CREATE_SESSION = """
INSERT INTO training_session(operator_id, config, status, total_questions)
VALUES (%s, %s::jsonb, 'RUNNING', %s)
RETURNING
  session_id,
  created_at::text AS created_at,
  status,
  total_questions
"""

TRAINING_INSERT_ITEM = """
INSERT INTO training_item(session_id, alert_payload, expected_action, status)
VALUES (%s, %s::jsonb, %s, 'PENDING')
RETURNING item_id
"""

TRAINING_NEXT_ITEM = """
SELECT item_id, alert_payload
FROM training_item
WHERE session_id = %s AND status = 'PENDING'
ORDER BY item_id ASC
LIMIT 1
"""

TRAINING_GET_ITEM = """
SELECT item_id, alert_payload
FROM training_item
WHERE session_id = %s AND item_id = %s
"""

TRAINING_MARK_ITEM_ANSWERED = """
UPDATE training_item
SET status = 'ANSWERED'
WHERE session_id = %s AND item_id = %s
"""

TRAINING_INSERT_ANSWER = """
INSERT INTO training_answer(
  item_id, session_id,
  operator_action, operator_reason,
  correct_action, is_correct, score,
  feedback_text, feedback_json
) VALUES (
  %s, %s,
  %s, %s,
  %s, %s, %s,
  %s, %s::jsonb
)
RETURNING answer_id
"""

TRAINING_AGG_SESSION = """
SELECT
  COUNT(*)::int AS answered,
  SUM(CASE WHEN is_correct THEN 1 ELSE 0 END)::int AS correct,
  SUM(CASE WHEN NOT is_correct THEN 1 ELSE 0 END)::int AS wrong
FROM training_answer
WHERE session_id = %s
"""

TRAINING_UPDATE_SESSION_STATS = """
UPDATE training_session
SET
  correct_count = %s,
  wrong_count   = %s,
  score_pct     = %s
WHERE session_id = %s
"""

TRAINING_FINISH_SESSION = """
UPDATE training_session
SET status='FINISHED', finished_at = NOW()
WHERE session_id = %s
"""

TRAINING_GET_SESSION = """
SELECT
  session_id,
  created_at::text AS created_at,
  finished_at::text AS finished_at,
  operator_id,
  status,
  config,
  total_questions,
  correct_count,
  wrong_count,
  score_pct
FROM training_session
WHERE session_id = %s
"""

TRAINING_LIST_SESSION_ANSWERS = """
SELECT
  answer_id,
  answered_at::text AS answered_at,
  item_id,
  operator_action,
  correct_action,
  is_correct,
  score,
  feedback_text
FROM training_answer
WHERE session_id = %s
ORDER BY answered_at ASC
"""
# ===== ML MODELS =====

ML_LIST_MODELS = """
SELECT
  version,
  date,
  status,
  artifact_path,
  is_active
FROM ia_model
ORDER BY date DESC;
"""

ML_GET_MODEL = """
SELECT
  version,
  date,
  status,
  artifact_path,
  is_active
FROM ia_model
WHERE version = %s;
"""

ML_GET_LATEST_METRICS = """
SELECT
  computed_at,
  split,
  threshold,
  metrics,
  confusion,
  dataset_ref,
  notes
FROM ia_model_metrics
WHERE model_version = %s
ORDER BY computed_at DESC
LIMIT 1;
"""

ML_GET_LATEST_IMPORTANCE = """
SELECT
  computed_at,
  method,
  importance,
  sample_info
FROM ia_model_feature_importance
WHERE model_version = %s AND method = %s
ORDER BY computed_at DESC
LIMIT 1;
"""