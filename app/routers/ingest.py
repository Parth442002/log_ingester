from fastapi import APIRouter, Depends,HTTPException
from sqlalchemy.exc import IntegrityError
from fastapi.encoders import jsonable_encoder
from sqlalchemy.orm import Session
from dateutil.parser import isoparse
from datetime import timezone
from app.database import get_db
from app.models import RawLog,LogStatusEnum
from app.schemas import BaseEventLog,EventTypeEnum
from app.celery_worker import compute_job_analytics
from app.utils import logger
from dateutil import tz

router = APIRouter()


@router.post("/logs/ingest")
def ingest_log(log: BaseEventLog, db: Session = Depends(get_db)):
    # 1) Normalize primary timestamp
    ts = log.timestamp
    # If it’s naive, assume UTC; otherwise convert to UTC
    if ts.tzinfo is None:
        ts = ts.replace(tzinfo=tz.UTC)
    else:
        ts = ts.astimezone(tz.UTC)

    # Build a JSON-friendly dict and normalize any other timestamps
    full_log = jsonable_encoder(log)
    full_log["timestamp"] = ts.isoformat()

    # normalize completion_time if present
    if "completion_time" in full_log:
        ct = isoparse(full_log["completion_time"])
        full_log["completion_time"] = ct.astimezone(timezone.utc).isoformat()

    try:
        raw_log = RawLog(
            job_id=log.job_id,
            event=log.event,
            user=log.user,
            timestamp=ts,
            task_id=log.task_id,
            log=full_log,
            status=LogStatusEnum.PENDING,
        )
        db.add(raw_log)
        db.commit()
        db.refresh(raw_log)
    except IntegrityError:
        db.rollback()
        logger.error(f"Duplicate log or constraint violation: {log}")
        raise HTTPException(400, "Duplicate log or constraint violation")

    # Only enqueue once we have both start & end events in the DB
    if log.event in (EventTypeEnum.SPARK_LISTENER_JOB_START, EventTypeEnum.SPARK_LISTENER_JOB_END):
        events = db.query(RawLog.event) \
                   .filter(RawLog.job_id == log.job_id) \
                   .distinct().all()
        present = {e[0] for e in events}
        if {EventTypeEnum.SPARK_LISTENER_JOB_START, EventTypeEnum.SPARK_LISTENER_JOB_END} \
           .issubset(present):
            compute_job_analytics.delay(log.job_id)

    return {
        "message": "Log ingested successfully",
        "log_id": str(raw_log.id)
    }