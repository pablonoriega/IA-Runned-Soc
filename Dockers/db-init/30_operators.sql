-- =========================================================
-- operators.sql
-- Crea tabla operators + trigger updated_at + índices + seed (10 operadores)
-- =========================================================

-- Si existe, elimina (permitido en tu caso)
DROP TABLE IF EXISTS operators CASCADE;

-- Tabla
CREATE TABLE operators (
  operator_id BIGSERIAL PRIMARY KEY,

  username TEXT UNIQUE NOT NULL,
  display_name TEXT NOT NULL,
  email TEXT,

  role TEXT NOT NULL DEFAULT 'tier1', -- tier1 | tier2 | lead | admin
  is_active BOOLEAN NOT NULL DEFAULT TRUE,

  max_active INT NOT NULL DEFAULT 10,
  timezone TEXT NOT NULL DEFAULT 'Europe/Madrid',
  shift_name TEXT,
  on_call BOOLEAN NOT NULL DEFAULT FALSE,

  sla_ack_seconds INT NOT NULL DEFAULT 900,
  sla_resolve_seconds INT NOT NULL DEFAULT 14400,
  business_hours_only BOOLEAN NOT NULL DEFAULT FALSE,

  skills JSONB NOT NULL DEFAULT '{}'::jsonb,

  -- útil si luego quieres balanceo por carga
  current_active INT NOT NULL DEFAULT 0,

  created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- Trigger updated_at (requiere que exista la función set_updated_at())
DROP TRIGGER IF EXISTS trg_operators_set_updated_at ON operators;
CREATE TRIGGER trg_operators_set_updated_at
BEFORE UPDATE ON operators
FOR EACH ROW EXECUTE FUNCTION set_updated_at();

-- Índices útiles para routing
CREATE INDEX IF NOT EXISTS idx_ops_active_role
ON operators(is_active, role);

CREATE INDEX IF NOT EXISTS idx_ops_active_oncall
ON operators(is_active, on_call);

CREATE INDEX IF NOT EXISTS idx_ops_skills
ON operators USING GIN (skills);

CREATE INDEX IF NOT EXISTS idx_ops_capacity
ON operators(current_active, max_active);

-- =========================================================
-- SEED DATA (10 operadores balanceados, sin "*")
-- =========================================================
INSERT INTO operators
(username, display_name, email, role, is_active,
 max_active, timezone, shift_name, on_call,
 sla_ack_seconds, sla_resolve_seconds, business_hours_only, skills)
VALUES

-- =========================
-- LEADS (3)
-- =========================

('sofia_lead','Sofía Martínez','sofia.martinez@example.com','lead',TRUE,4,'Europe/Madrid','mañana',FALSE,300,7200,FALSE,
'{"alert_types":["malware_detected","ransomware_activity","phishing_email","credential_dump_detected","suspicious_login","brute_force_attempt","port_scan","command_and_control","data_exfiltration","privilege_escalation"],
"attack_phases":["reconnaissance","initial_access","execution","lateral_movement","exfiltration"],"min_severity":4}'::jsonb),

('pablo_lead','Pablo Ortega','pablo.ortega@example.com','lead',TRUE,4,'Europe/Madrid','tarde',FALSE,300,7200,FALSE,
'{"alert_types":["malware_detected","ransomware_activity","phishing_email","credential_dump_detected","suspicious_login","brute_force_attempt","port_scan","command_and_control","data_exfiltration","privilege_escalation"],
"attack_phases":["reconnaissance","initial_access","execution","lateral_movement","exfiltration"],"min_severity":4}'::jsonb),

('lucia_lead','Lucía Vega','lucia.vega@example.com','lead',TRUE,4,'Europe/Madrid','noche',FALSE,300,7200,FALSE,
'{"alert_types":["malware_detected","ransomware_activity","phishing_email","credential_dump_detected","suspicious_login","brute_force_attempt","port_scan","command_and_control","data_exfiltration","privilege_escalation"],
"attack_phases":["reconnaissance","initial_access","execution","lateral_movement","exfiltration"],"min_severity":4}'::jsonb),

-- =========================
-- TIER 2 (7)
-- =========================

('laura_t2','Laura Sánchez','laura.sanchez@example.com','tier2',TRUE,6,'Europe/Madrid','mañana',FALSE,600,10800,FALSE,
'{"alert_types":["malware_detected","command_and_control","ransomware_activity"],"attack_phases":["execution","lateral_movement"],"min_severity":2}'::jsonb),

('sergio_t2','Sergio Vidal','sergio.vidal@example.com','tier2',TRUE,6,'Europe/Madrid','mañana',FALSE,600,10800,FALSE,
'{"alert_types":["ransomware_activity","malware_detected","privilege_escalation"],"attack_phases":["execution","lateral_movement"],"min_severity":3}'::jsonb),

('marco_t2','Marco Rivas','marco.rivas@example.com','tier2',TRUE,6,'Europe/Madrid','tarde',FALSE,600,10800,FALSE,
'{"alert_types":["data_exfiltration","credential_dump_detected","privilege_escalation"],"attack_phases":["exfiltration","lateral_movement"],"min_severity":3}'::jsonb),

('ines_t2','Inés Blanco','ines.blanco@example.com','tier2',TRUE,6,'Europe/Madrid','noche',FALSE,600,10800,FALSE,
'{"alert_types":["command_and_control","malware_detected","data_exfiltration"],"attack_phases":["execution","exfiltration"],"min_severity":3}'::jsonb),

('raquel_t2','Raquel Torres','raquel.torres@example.com','tier2',TRUE,6,'Europe/Madrid','mañana',FALSE,600,10800,FALSE,
'{"alert_types":["credential_dump_detected","privilege_escalation","command_and_control"],"attack_phases":["execution","lateral_movement"],"min_severity":3}'::jsonb),

('hugo_t2','Hugo Serrano','hugo.serrano@example.com','tier2',TRUE,6,'Europe/Madrid','tarde',FALSE,600,10800,FALSE,
'{"alert_types":["malware_detected","command_and_control","data_exfiltration"],"attack_phases":["execution","exfiltration"],"min_severity":3}'::jsonb),

('carmen_t2','Carmen Pardo','carmen.pardo@example.com','tier2',TRUE,6,'Europe/Madrid','noche',FALSE,600,10800,FALSE,
'{"alert_types":["data_exfiltration","command_and_control","malware_detected"],"attack_phases":["exfiltration","execution"],"min_severity":3}'::jsonb),

-- =========================
-- TIER 1 (15)
-- =========================

('ana_t1','Ana Gómez','ana.gomez@example.com','tier1',TRUE,10,'Europe/Madrid','mañana',FALSE,900,14400,TRUE,
'{"alert_types":["phishing_email","suspicious_login","credential_dump_detected"],"attack_phases":["initial_access"],"min_severity":1}'::jsonb),

('carlos_t1','Carlos Pérez','carlos.perez@example.com','tier1',TRUE,10,'Europe/Madrid','tarde',FALSE,900,14400,TRUE,
'{"alert_types":["port_scan","brute_force_attempt","suspicious_login"],"attack_phases":["reconnaissance"],"min_severity":1}'::jsonb),

('maria_t1','María Ruiz','maria.ruiz@example.com','tier1',TRUE,8,'Europe/Madrid','noche',FALSE,900,14400,FALSE,
'{"alert_types":["phishing_email","credential_dump_detected","brute_force_attempt"],"attack_phases":["initial_access"],"min_severity":1}'::jsonb),

('diego_t1','Diego Navarro','diego.navarro@example.com','tier1',TRUE,9,'Europe/Madrid','tarde',FALSE,900,14400,TRUE,
'{"alert_types":["port_scan","brute_force_attempt","privilege_escalation"],"attack_phases":["reconnaissance","initial_access"],"min_severity":2}'::jsonb),

('julia_t1','Julia Ramos','julia.ramos@example.com','tier1',TRUE,10,'Europe/Madrid','mañana',FALSE,900,14400,TRUE,
'{"alert_types":["phishing_email","suspicious_login","brute_force_attempt"],"attack_phases":["initial_access"],"min_severity":1}'::jsonb),

('andres_t1','Andrés Molina','andres.molina@example.com','tier1',TRUE,10,'Europe/Madrid','mañana',FALSE,900,14400,TRUE,
'{"alert_types":["port_scan","brute_force_attempt","phishing_email"],"attack_phases":["reconnaissance"],"min_severity":1}'::jsonb),

('nuria_t1','Nuria Castillo','nuria.castillo@example.com','tier1',TRUE,10,'Europe/Madrid','tarde',FALSE,900,14400,TRUE,
'{"alert_types":["port_scan","brute_force_attempt","suspicious_login"],"attack_phases":["reconnaissance","initial_access"],"min_severity":1}'::jsonb),

('alvaro_t1','Álvaro Peña','alvaro.pena@example.com','tier1',TRUE,10,'Europe/Madrid','tarde',FALSE,900,14400,TRUE,
'{"alert_types":["phishing_email","suspicious_login","credential_dump_detected"],"attack_phases":["initial_access"],"min_severity":1}'::jsonb),

('silvia_t1','Silvia Ibáñez','silvia.ibanez@example.com','tier1',TRUE,10,'Europe/Madrid','tarde',FALSE,900,14400,TRUE,
'{"alert_types":["port_scan","brute_force_attempt","phishing_email"],"attack_phases":["reconnaissance"],"min_severity":1}'::jsonb),

('david_t1','David Fuentes','david.fuentes@example.com','tier1',TRUE,9,'Europe/Madrid','tarde',FALSE,900,14400,TRUE,
'{"alert_types":["suspicious_login","brute_force_attempt","malware_detected"],"attack_phases":["initial_access"],"min_severity":2}'::jsonb),

('irene_t1','Irene Soto','irene.soto@example.com','tier1',TRUE,8,'Europe/Madrid','noche',FALSE,900,14400,FALSE,
'{"alert_types":["phishing_email","suspicious_login","brute_force_attempt"],"attack_phases":["initial_access"],"min_severity":1}'::jsonb),

('oscar_t1','Óscar León','oscar.leon@example.com','tier1',TRUE,8,'Europe/Madrid','noche',FALSE,900,14400,FALSE,
'{"alert_types":["port_scan","brute_force_attempt","phishing_email"],"attack_phases":["reconnaissance"],"min_severity":1}'::jsonb),

('patricia_t1','Patricia Vidal','patricia.vidal@example.com','tier1',TRUE,8,'Europe/Madrid','noche',FALSE,900,14400,FALSE,
'{"alert_types":["suspicious_login","credential_dump_detected","phishing_email"],"attack_phases":["initial_access"],"min_severity":2}'::jsonb),

('jorge_t1','Jorge Nieto','jorge.nieto@example.com','tier1',TRUE,10,'Europe/Madrid','mañana',FALSE,900,14400,TRUE,
'{"alert_types":["port_scan","brute_force_attempt","phishing_email"],"attack_phases":["reconnaissance"],"min_severity":1}'::jsonb),

('elena_t1','Elena Campos','elena.campos@example.com','tier1',TRUE,10,'Europe/Madrid','mañana',FALSE,900,14400,TRUE,
'{"alert_types":["phishing_email","suspicious_login","credential_dump_detected"],"attack_phases":["initial_access"],"min_severity":1}'::jsonb)

ON CONFLICT (username) DO NOTHING;