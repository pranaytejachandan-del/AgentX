from pydantic import BaseModel
from typing import Optional


class RootResponse(BaseModel):
    status: str = "ok"
    service: str = "AgentX"


class HealthCheckResponse(BaseModel):
    status: str
    service: str = "AgentX"
    database: str
    detail: Optional[str] = None
