from pydantic import BaseModel, Field
from datetime import datetime

class BaseEventLog(BaseModel):
    event: str
    job_id: int
    timestamp: datetime

    class Config:
        extra = "allow"  # allow other fields (e.g., task_id, duration_ms, etc.)
