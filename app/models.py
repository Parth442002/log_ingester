from sqlalchemy import Column, Integer, String, JSON, DateTime
from datetime import datetime
from .database import Base


class RawLog(Base):
    __tablename__ = "raw_logs"

    id = Column(Integer, primary_key=True, index=True)
    job_id = Column(Integer, index=True)
    event_type = Column(String, index=True)
    log = Column(JSON, nullable=False)
    ingestion_time = Column(DateTime, default=datetime.now)
    status = Column(String, default="pending")  # for background worker