from pydantic import BaseModel, Field
from typing import Optional, List, Literal, Any, Dict

DecisionType = Literal["ACCEPT", "REJECT"]

class DecisionRequest(BaseModel):
    decision: DecisionType
    final_action: str = Field(..., description="Acción final seleccionada por el analista")
    reason: Optional[str] = Field(default=None, description="Motivo de aceptación/rechazo")
    decided_by: str = Field(..., description="Usuario/operador SOC que decide")
    ai_explanation: Optional[str] = Field(
    default=None,
    description="Explicación generada por IA sobre por qué se recomendó la acción"
    )


class AlertSummary(BaseModel):
    alert_id: int
    created_at: str
    timestamp_utc: str
    alert_type: str
    attack_phase: str
    asset_type: str
    asset_criticality: str
    severity: int
    src_ip: str
    ip_reputation: str
    repeat_offender: bool
    status: str
    model_recommended_action: Optional[str] = None
    model_confidence: Optional[float] = None
    assigned_to: Optional[str] = None
    assigned_at: Optional[str] = None
    closed_at: Optional[str] = None
    human_decision: Optional[str] = None
    human_decided_by: Optional[str] = None
    human_reason: Optional[str] = None

class AlertDetail(BaseModel):
    alert_id: int
    created_at: str
    source_system: Optional[str] = None

    alert_type: str
    attack_phase: str
    asset_type: str
    asset_criticality: str
    severity: int
    timestamp_utc: str
    is_business_hours: bool
    detection_source: str
    confidence: float
    src_ip: str
    asset_exposure: str
    src_country: str
    geo_anomaly: bool
    ip_reputation: str
    repeat_offender: bool
    previous_incidents_30d: int
    event_count: int
    time_window_minutes: int
    user_role: str
    is_privileged_account: bool
    isolation_supported: bool
    downtime_tolerance: str

    # workflow/model
    status: str
    assigned_to:  Optional[str] = None
    assigned_at: Optional[str] = None
    closed_at: Optional[str] = None
    execution_status: Optional[str] = None
    model_version: Optional[str] = None
    model_recommended_action: Optional[str] = None
    model_confidence: Optional[float] = None
    model_top_k: Optional[Any] = None

    human_decision: Optional[str] = None
    human_final_action: Optional[str] = None
    human_reason: Optional[str] = None
    human_decided_by: Optional[str] = None
    human_decided_at: Optional[str] = None

    ai_explanation: Optional[str] = None

    raw_payload: Optional[Dict[str, Any]] = None
class EventItem(BaseModel):
    event_id: int
    event_time: str
    event_type: str
    actor: str
    details: Optional[Any] = None

class PagedAlerts(BaseModel):
    items: List[AlertSummary]
    limit: int
    offset: int
    total: int

class OperatorItem(BaseModel):
    operator_id: int
    username: str
    display_name: str
    email: Optional[str] = None
    role: str
    is_active: bool

    max_active: int
    timezone: str
    shift_name: Optional[str] = None
    on_call: bool

    sla_ack_seconds: int
    sla_resolve_seconds: int
    business_hours_only: bool

    skills: Dict[str, Any]
    active_assigned: int

    created_at: str
    updated_at: str

    currentAlarmsCount: int = 0

class OperatorsResponse(BaseModel):
    items: List[OperatorItem]

class OperatorSlaItem(BaseModel):
    alert_id: int
    assigned_to: Optional[str] = None
    assigned_at: str
    closed_at: str
    resolve_seconds: int

class OperatorSlaStats(BaseModel):
    total: int
    considered: int
    target_seconds: int
    avg_seconds: Optional[float] = None
    median_seconds: Optional[int] = None
    p90_seconds: Optional[int] = None
    compliance_pct: Optional[int] = None

class OperatorSlaResponse(BaseModel):
    items: List[OperatorSlaItem]
    limit: int
    offset: int
    total: int
    stats: OperatorSlaStats

class SocMetricStats(BaseModel):
    considered: int
    avg_seconds: Optional[float] = None
    median_seconds: Optional[int] = None
    p90_seconds: Optional[int] = None

class SocMetricsResponse(BaseModel):
    resolve: SocMetricStats
    ack: SocMetricStats

class LatestModelResponse(BaseModel):
    version: str
    date: str

DatasetType = Literal["rejected_only", "all_closed"]

class RetrainRequest(BaseModel):
    type: Literal["RETRAIN_MODEL"]
    run_immediately: bool
    when: Optional[str] = None  # viene como datetime-local string
    dataset: DatasetType

TrainingStatus = Literal["RUNNING", "FINISHED", "ABORTED"]

class TrainingSessionSummary(BaseModel):
    session_id: int
    created_at: str
    finished_at: Optional[str] = None
    operator_id: str
    status: TrainingStatus
    total_questions: int
    correct_count: int
    wrong_count: int
    score_pct: float

class TrainingSessionsResponse(BaseModel):
    items: List[TrainingSessionSummary]

class TrainingCreateRequest(BaseModel):
    operator_id: str = Field(default="unknown")
    total_questions: int = Field(default=10, ge=1, le=200)
    config: Dict[str, Any]

class TrainingCreateResponse(BaseModel):
    session_id: int
    created_at: str
    status: TrainingStatus
    total_questions: int

class TrainingNextItemResponse(BaseModel):
    item_id: Optional[int] = None
    alert_payload: Optional[Dict[str, Any]] = None

class TrainingAnswerRequest(BaseModel):
    item_id: int
    operator_action: str
    operator_reason: str

class TrainingGrade(BaseModel):
    correct_action: str
    is_correct: bool
    score: float = 0
    feedback_text: str
    feedback_json: Optional[Dict[str, Any]] = None

class TrainingAnswerResponse(BaseModel):
    grade: TrainingGrade
    progress: Dict[str, Any]

class TrainingSessionDetail(BaseModel):
    session_id: int
    created_at: str
    finished_at: Optional[str] = None
    operator_id: str
    status: TrainingStatus
    config: Dict[str, Any]
    total_questions: int
    correct_count: int
    wrong_count: int
    score_pct: float

class TrainingAnswerItem(BaseModel):
    answer_id: int
    answered_at: str
    item_id: int
    operator_action: str
    correct_action: str
    is_correct: bool
    score: float
    feedback_text: str

class TrainingSessionDetailResponse(BaseModel):
    session: Optional[TrainingSessionDetail] = None
    answers: List[TrainingAnswerItem] = []

class MlModelRow(BaseModel):
    version: str
    date: Optional[str] = None
    status: Optional[str] = None
    artifact_path: Optional[str] = None
    is_active: bool = False


class MlModelsListResponse(BaseModel):
    active_version: Optional[str] = None
    models: List[MlModelRow] = []


class MlModelMetrics(BaseModel):
    computed_at: Optional[str] = None
    split: Optional[str] = None
    threshold: Optional[float] = None
    metrics: Dict[str, Any] = {}
    confusion: Dict[str, Any] = {}
    dataset_ref: Optional[str] = None
    notes: Optional[str] = None


class MlModelDetailResponse(BaseModel):
    model: Optional[MlModelRow] = None
    latest_metrics: Optional[MlModelMetrics] = None
    importances: Dict[str, Any] = {}