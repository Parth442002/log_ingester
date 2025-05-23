# celery_worker.py
from celery import Celery
from sqlalchemy.orm import Session
from app.database import SessionLocal
from app.models import RawLog, JobAnalytics
from app.schemas import EventTypeEnum,LogStatusEnum
import logging
from datetime import datetime

celery_app = Celery(
    "worker",
    broker="redis://localhost:6379/0",  # or "redis://redis:6379/0" if using Docker
    backend="redis://localhost:6379/0"
)



@celery_app.task(name="tasks.compute_job_analytics")
def compute_job_analytics(job_id: int):
    db: Session = SessionLocal()
    try:
        logs = (
            db.query(RawLog)
            .filter(RawLog.job_id == job_id, RawLog.status == LogStatusEnum.PENDING)
            .all()
        )

        if not logs:
            logging.info(f"No pending logs found for job {job_id}, skipping.")
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
            logging.info(f"Job {job_id} analytics deferred: missing start/end logs.")
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
        logging.info(f"Analytics computed and saved for job {job_id}")

    except Exception as e:
        db.rollback()
        logging.error(f"Failed to compute analytics for job {job_id}: {e}")
        raise
    finally:
        db.close()