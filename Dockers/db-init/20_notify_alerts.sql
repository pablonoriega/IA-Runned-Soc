-- INSERT: alerta creada / workflow creado
CREATE OR REPLACE FUNCTION notify_workflow_insert()
RETURNS trigger AS $$
DECLARE
  payload json;
BEGIN
  payload := json_build_object(
    'event', 'ALERT_INSERTED',
    'alert_id', NEW.alert_id,
    'status', NEW.status
  );

  PERFORM pg_notify('alerts_channel', payload::text);
  RETURN NEW;
END;
$$ LANGUAGE plpgsql;

DROP TRIGGER IF EXISTS trg_notify_workflow_insert ON alert_workflow;

CREATE TRIGGER trg_notify_workflow_insert
AFTER INSERT ON alert_workflow
FOR EACH ROW
EXECUTE FUNCTION notify_workflow_insert();


-- UPDATE: cambio de estado (solo si realmente cambia status)
CREATE OR REPLACE FUNCTION notify_workflow_update()
RETURNS trigger AS $$
DECLARE
  payload json;
BEGIN
  -- Evita notificar updates que no cambian el status
  IF (NEW.status IS NOT DISTINCT FROM OLD.status) THEN
    RETURN NEW;
  END IF;

  payload := json_build_object(
    'event', 'ALERT_STATUS_CHANGED',
    'alert_id', NEW.alert_id,
    'old_status', OLD.status,
    'status', NEW.status
  );

  PERFORM pg_notify('alerts_channel', payload::text);
  RETURN NEW;
END;
$$ LANGUAGE plpgsql;

DROP TRIGGER IF EXISTS trg_notify_workflow_update ON alert_workflow;

CREATE TRIGGER trg_notify_workflow_update
AFTER UPDATE ON alert_workflow
FOR EACH ROW
EXECUTE FUNCTION notify_workflow_update();
