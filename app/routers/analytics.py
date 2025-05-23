from fastapi import APIRouter, Depends, HTTPException,Query
from datetime import datetime
from typing import List
import json
from sqlalchemy import cast, Date
from sqlalchemy.orm import Session
from app.database import get_db
from app.models import JobAnalytics
from app.schemas import JobAnalyticsResponse
from app.celery_worker import compute_job_analytics
from app.utils.redis_client import redis_client
from app.utils.config import CACHING_TTL
from app.utils.logger import logger

router = APIRouter(
    prefix="/analytics",
    tags=["Analytics"]
)


@router.get("/jobs/{job_id}", response_model=JobAnalyticsResponse)
def get_job_analytics(job_id: int, db: Session = Depends(get_db)):
    cached = redis_client.get(f"job_analytics:{job_id}")
    if cached:
        logger.success(f"Job analytics for job_id {job_id} retrieved from Redis.")
        return JobAnalyticsResponse.model_validate(json.loads(cached))

    analytics = db.query(JobAnalytics).filter(JobAnalytics.job_id == job_id).first()

    if analytics:
        # Convert SQLAlchemy model to dict using Pydantic
        analytics_data = JobAnalyticsResponse.model_validate(analytics).model_dump_json()
        redis_client.set(f"job_analytics:{job_id}", analytics_data, ex=CACHING_TTL)
        return analytics

    logger.warning(f"Job analytics for job_id {job_id} not found in DB, triggering computation.")
    compute_job_analytics.delay(job_id)
    raise HTTPException(
        status_code=202,
        detail=f"Analytics for job_id {job_id} are being processed. Please check back later."
    )


@router.get("/summary", response_model=List[JobAnalyticsResponse])
def get_analytics_summary(date_str: str = Query(..., alias="date"), db: Session = Depends(get_db)):
    try:
        query_date = datetime.strptime(date_str, "%Y-%m-%d").date()
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid date format. Use YYYY-MM-DD.")

    cached = redis_client.get(f"analytics_summary:{date_str}")
    if cached:
        logger.success(f"Analytics summary for date {date_str} retrieved from Redis.")
        return [JobAnalyticsResponse.model_validate(json.loads(c)) for c in json.loads(cached)]

    analytics_list = (
        db.query(JobAnalytics)
        .filter(cast(JobAnalytics.end_time, Date) == query_date)
        .all()
    )

    if not analytics_list:
        raise HTTPException(status_code=404, detail=f"No job analytics found for date {date_str}")

    # Convert list of SQLAlchemy models to list of dicts using Pydantic
    analytics_response = [JobAnalyticsResponse.model_validate(a).model_dump_json() for a in analytics_list]
    redis_client.set(f"analytics_summary:{date_str}", json.dumps(analytics_response), ex=CACHING_TTL)

    return analytics_list