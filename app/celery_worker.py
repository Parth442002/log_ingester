# celery_worker.py
from celery import Celery
from sqlalchemy.orm import Session
from app.database import SessionLocal
from app.models import RawLog, JobAnalytics
from app.schemas import EventTypeEnum,LogStatusEnum
from datetime import datetime
from app.utils.config import CELERY_BROKER_URL, CELERY_RESULT_BACKEND
from app.utils.logger import logger
from app.utils.redis_client import redis_client

celery_app = Celery(
    "worker",
    broker=CELERY_BROKER_URL,
    backend=CELERY_RESULT_BACKEND
)



@celery_app.task(name="tasks.compute_job_analytics")
def compute_job_analytics(job_id: int):
    """
    Compute and store job analytics for the given job_id.

    1. Fetch pending logs for job_id.
    2. Identify start, end, and task-end events.
    3. If both start and end exist, calculate duration, task count,
       failed tasks, and success rate.
    4. Upsert into JobAnalytics and mark logs as processed.
    """
    db: Session = SessionLocal()
    try:
        logs = (
            db.query(RawLog)
            .filter(RawLog.job_id == job_id, RawLog.status == LogStatusEnum.PENDING)
            .all()
        )

        if not logs:
            logger.info(f"No pending logs found for job {job_id}, skipping.")
            return

        # Initialize variables
        job_start = None
        job_end = None
        task_ends = []

        # Categorize logs efficiently in a single pass
        for log in logs:
            if log.event == EventTypeEnum.SPARK_LISTENER_JOB_START:
                job_start = log
            elif log.event == EventTypeEnum.SPARK_LISTENER_JOB_END:
                job_end = log
            elif log.event == EventTypeEnum.SPARK_LISTENER_TASK_END:
                task_ends.append(log)

        # Ensure required events exist
        if not job_start or not job_end:
            logger.info(f"Job {job_id} analytics deferred: missing start/end logs.")
            return  # Wait for all required logs

        # Parse timestamps
        start_time = datetime.fromisoformat(job_start.log["timestamp"].replace("Z", "+00:00"))
        end_time = datetime.fromisoformat(job_end.log["completion_time"].replace("Z", "+00:00"))

        # Compute analytics
        duration = int((end_time - start_time).total_seconds())
        task_count = len(task_ends)
        failed_tasks = sum(1 for t in task_ends if not t.log.get("successful", True))
        success_rate = round(((task_count - failed_tasks) / task_count) * 100, 2) if task_count else 0.0

        # Create or update analytics row
        analytics_record = JobAnalytics(
            job_id=job_id,
            user=job_start.log.get("user"),
            start_time=start_time,
            end_time=end_time,
            duration_seconds=duration,
            task_count=task_count,
            failed_tasks=failed_tasks,
            success_rate=success_rate,
        )
        db.merge(analytics_record)


        # Mark logs as processed
        for log in logs:
            log.status = LogStatusEnum.PROCESSED

        db.commit()

        #Evict cache for job analytics and daily summary
        redis_client.delete(f"job_analytics:{job_id}")
        date_key = analytics_record.end_time.date().isoformat()
        redis_client.delete(f"analytics_summary:{date_key}")

        logger.success(f"Analytics computed and saved for job {job_id}")

    except Exception as e:
        db.rollback()
        logger.error(f"Failed to compute analytics for job {job_id}: {e}")
        raise
    finally:
        db.close()