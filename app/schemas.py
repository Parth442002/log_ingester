import uuid
from pydantic import BaseModel
from datetime import datetime
from enum import Enum
from typing import Optional, Any, Dict
#
class EventTypeEnum(str, Enum):
    SPARK_LISTENER_JOB_START = "SparkListenerJobStart"
    SPARK_LISTENER_TASK_END = "SparkListenerTaskEnd"
    SPARK_LISTENER_JOB_END = "SparkListenerJobEnd"


class LogStatusEnum(str, Enum):
    PENDING = "pending"
    PROCESSED = "processed"


class BaseEventLog(BaseModel):
    event: EventTypeEnum
    job_id: int
    timestamp: datetime
    user: Optional[str] = None
    task_id: Optional[str] = None

    class Config:
        use_enum_values = True
        extra = "allow"


class RawLogCreate(BaseEventLog):
    """Model used to ingest logs from the API"""
    pass


class RawLogResponse(BaseModel):
    """Model for response and internal usage"""
    id: uuid.UUID
    event: EventTypeEnum
    job_id: int
    timestamp: datetime
    user: Optional[str]
    log: Dict[str, Any]
    insertion_time: datetime
    status: LogStatusEnum

    class Config:
        orm_mode = True
        use_enum_values = True


class JobAnalyticsResponse(BaseModel):
    job_id: int
    user: str
    start_time: datetime
    end_time: datetime
    duration_seconds: int
    task_count: int
    failed_tasks: int
    success_rate: float

    class Config:
        orm_mode = True
        use_enum_values = True
        from_attributes=True