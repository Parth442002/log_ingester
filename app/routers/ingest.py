from fastapi import APIRouter, Depends,HTTPException
from sqlalchemy.exc import IntegrityError
from fastapi.encoders import jsonable_encoder
from sqlalchemy.orm import Session
from app.database import get_db
from app.models import RawLog
from app.schemas import BaseEventLog,EventTypeEnum
from app.celery_worker import compute_job_analytics

router = APIRouter()


@router.post("/logs/ingest")
def ingest_log(log: BaseEventLog, db: Session = Depends(get_db)):
    job_id = log.job_id
    event_type = log.event
    user = log.user
    timestamp = log.timestamp

    # Convert to JSON-compatible dict including dynamic fields
    full_log_dict = jsonable_encoder(log)

    try:
        raw_log = RawLog(
            job_id=job_id,
            event=event_type,
            user=user,
            timestamp=timestamp,
            log=full_log_dict
        )
        db.add(raw_log)
        db.commit()
        db.refresh(raw_log)
    except IntegrityError:
        db.rollback()
        raise HTTPException(status_code=400, detail="Duplicate log or constraint violation")

    # Check if both JobStart & JobEnd exist for this job_id
    if event_type in (EventTypeEnum.SPARK_LISTENER_JOB_START, EventTypeEnum.SPARK_LISTENER_JOB_END):
        events = db.query(RawLog.event).filter(RawLog.job_id == job_id).distinct().all()
        event_types_present = {e[0] for e in events}
        if (
            EventTypeEnum.SPARK_LISTENER_JOB_START in event_types_present and
            EventTypeEnum.SPARK_LISTENER_JOB_END in event_types_present
        ):
            compute_job_analytics.delay(job_id)

    return {
        "message": "Log ingested successfully",
        "log_id": str(raw_log.id)
    }