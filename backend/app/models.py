from datetime import datetime, timezone
from typing import Optional, List, Dict
from sqlmodel import SQLModel, Field, JSON


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


class Asset(SQLModel, table=True):
    id: str = Field(primary_key=True)
    name: str
    resource_type: str  # "Cloud Run", "Cloud Function", "GKE", "Vertex AI"
    region: str
    runtime: Optional[str] = None
    service_account: Optional[str] = None
    env_vars: Dict[str, str] = Field(default_factory=dict, sa_type=JSON)
    labels: Dict[str, str] = Field(default_factory=dict, sa_type=JSON)
    is_ai_agent: bool = False
    confidence_score: int = 0
    confidence_reasons: List[str] = Field(default_factory=list, sa_type=JSON)
    risk_score: int = 0
    risk_reasons: List[str] = Field(default_factory=list, sa_type=JSON)
    last_seen: datetime = Field(default_factory=utc_now)

class Scan(SQLModel, table=True):
    id: str = Field(primary_key=True)
    timestamp: datetime = Field(default_factory=utc_now)
    status: str  # "running", "completed", "failed"
    assets_found: int = 0
    agents_found: int = 0
    error_message: Optional[str] = None
