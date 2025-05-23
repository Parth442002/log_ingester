from fastapi import APIRouter, Depends, HTTPException,Query
from datetime import datetime, date
from typing import List
from sqlalchemy import cast, Date
from sqlalchemy.orm import Session
from app.database import get_db
from app.models import JobAnalytics
from app.schemas import JobAnalyticsResponse
from app.celery_worker import compute_job_analytics
import logging

router = APIRouter(
    prefix="/analytics",
    tags=["Analytics"]
)


@router.get("/analytics/jobs/{job_id}", response_model=JobAnalyticsResponse)
def get_job_analytics(job_id: int, db: Session = Depends(get_db)):
    analytics = db.query(JobAnalytics).filter(JobAnalytics.job_id == job_id).first()

    if analytics:
        return analytics

    logging.info(f"Job analytics for job_id {job_id} not found in the database, triggering computation.")
    compute_job_analytics.delay(job_id)
    raise HTTPException(
        status_code=202,
        detail=f"Analytics for job_id {job_id} are being processed. Please check back later."
    )


@router.get("/analytics/summary", response_model=List[JobAnalyticsResponse])
def get_analytics_summary(date_str: str = Query(..., alias="date"), db: Session = Depends(get_db)):
    try:
        query_date = datetime.strptime(date_str, "%Y-%m-%d").date()
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid date format. Use YYYY-MM-DD.")

    # Filter by the date part of end_time (jobs completed on that date)
    analytics_list = (
        db.query(JobAnalytics)
        .filter(cast(JobAnalytics.end_time, Date) == query_date)
        .all()
    )

    if not analytics_list:
        raise HTTPException(status_code=404, detail=f"No job analytics found for date {date_str}")

    return analytics_list