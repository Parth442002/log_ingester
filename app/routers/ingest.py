from fastapi import APIRouter, Depends, HTTPException
from fastapi.encoders import jsonable_encoder
from sqlalchemy.orm import Session
from app.database import SessionLocal
from app.models import RawLog
from app.schemas import BaseEventLog
import datetime

router = APIRouter()

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

@router.post("/logs/ingest")
def ingest_log(log: BaseEventLog, db: Session = Depends(get_db)):
    job_id=log.job_id
    event_type=log.event
    data=jsonable_encoder(log)
    raw_log = RawLog(
        job_id=job_id,
        event_type=event_type,
        log=data
    )
    db.add(raw_log)
    db.commit()
    db.refresh(raw_log)

    return {"message": "Log ingested", "log_id": raw_log.id}