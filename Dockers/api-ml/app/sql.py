SELECT_TRAINING_REJECTED_ONLY = """
SELECT
  a.alert_id, 
  a.alert_type,
  a.attack_phase,
  a.asset_type,
  a.asset_criticality,
  a.severity,
  a.is_business_hours,
  a.detection_source,
  a.confidence,
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
  a.timestamp_utc,
  a.src_ip,

  CASE
    WHEN w.human_decision = 'ACCEPT' THEN w.model_recommended_action
    WHEN w.human_decision = 'REJECT' THEN w.human_final_action
    ELSE NULL
  END AS recommended_action

FROM alerts a
JOIN alert_workflow w ON w.alert_id = a.alert_id
WHERE w.status = 'CLOSED'
  AND w.human_decision = 'REJECT'
  AND w.human_final_action IS NOT NULL;
"""


SELECT_TRAINING_ALL_CLOSED = """
SELECT
  a.alert_id, 
  a.alert_type,
  a.attack_phase,
  a.asset_type,
  a.asset_criticality,
  a.severity,
  a.is_business_hours,
  a.detection_source,
  a.confidence,
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
  a.timestamp_utc,
  a.src_ip,

  CASE
    WHEN w.human_decision = 'ACCEPT' THEN w.model_recommended_action
    WHEN w.human_decision = 'REJECT' THEN w.human_final_action
    ELSE NULL
  END AS recommended_action

FROM alerts a
JOIN alert_workflow w ON w.alert_id = a.alert_id
WHERE w.status = 'CLOSED'
  AND w.human_decision IN ('ACCEPT','REJECT')
  AND (
    (w.human_decision = 'ACCEPT' AND w.model_recommended_action IS NOT NULL)
    OR
    (w.human_decision = 'REJECT' AND w.human_final_action IS NOT NULL)
  );
"""