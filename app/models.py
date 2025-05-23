from sqlalchemy import Column, Integer, String, JSON, DateTime,Float,UniqueConstraint,func,Enum
from sqlalchemy.dialects.postgresql import UUID
import uuid
import enum
from .database import Base


class EventTypeEnum(str, enum.Enum):
    SPARK_LISTENER_JOB_START = "SparkListenerJobStart"
    SPARK_LISTENER_TASK_END = "SparkListenerTaskEnd"
    SPARK_LISTENER_JOB_END = "SparkListenerJobEnd"

class LogStatusEnum(str, enum.Enum):
    PENDING = "pending"
    PROCESSED = "processed"


class RawLog(Base):
    __tablename__ = "raw_logs"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, unique=True, nullable=False)
    event = Column(Enum(EventTypeEnum), nullable=False)
    job_id = Column(Integer, nullable=False, index=True)
    user =Column(String,index=True,nullable=True)
    timestamp = Column(DateTime(timezone=True), nullable=False)
    log = Column(JSON, nullable=False)  # full event payload as JSON
    insertion_time = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    status = Column(Enum(LogStatusEnum), default=LogStatusEnum.PENDING, nullable=False)

    __table_args__ = (
        UniqueConstraint('job_id', 'event_type', 'log->>\'task_id\'', name='uq_job_event_task'),
    )


class JobAnalytics(Base):
    __tablename__ = "job_analytics"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, unique=True, nullable=False)
    job_id = Column(Integer, index=True, nullable=False, unique=True)  # Each job has one analytics row
    user = Column(String, index=True, nullable=False)

    start_time = Column(DateTime(timezone=True), nullable=False)
    end_time = Column(DateTime(timezone=True), nullable=False)
    duration_seconds = Column(Integer, nullable=False)

    task_count = Column(Integer, nullable=False)
    failed_tasks = Column(Integer, nullable=False)
    success_rate = Column(Float, nullable=False)

    insertion_time = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    __table_args__ = (
        UniqueConstraint("job_id", name="uq_job_analytics_job_id"),
    )