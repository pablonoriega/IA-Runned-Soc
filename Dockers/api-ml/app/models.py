from pydantic import BaseModel, Field
from typing import Optional, Literal, Dict

# ===== Requests =====

class PredictRequest(BaseModel):
    data: Dict
    top_k: int = 3  # cuántas alternativas devolver


class RetrainRunRequest(BaseModel):
    type: Literal["RETRAIN_MODEL"] = Field(..., description="Tipo de evento")
    version: str = Field(..., min_length=1, description="ID/version del job de reentreno")
    scheduled_for: Optional[str] = Field(default=None, description="ISO datetime (UTC)")
    run_immediately: bool = Field(default=False)
    when: Optional[str] = Field(default=None, description="datetime-local original (sin TZ)")
    dataset: Optional[str] = Field(default=None, description="rejected_only | all_closed (opcional)")