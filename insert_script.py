import random
from sqlalchemy.exc import SQLAlchemyError
from datetime import datetime, timedelta
from sqlalchemy.orm import Session
from app.database import get_db
from app.models import RawLog, EventTypeEnum, LogStatusEnum

def create_job_logs(job_id: int, start_time: datetime):
    logs = []

    # 1) Job Start log
    job_start_log = RawLog(
        event=EventTypeEnum.SPARK_LISTENER_JOB_START,
        job_id=job_id,
        user=f"user{job_id}@example.com",
        timestamp=start_time,
        task_id=None,
        log={
            "event": EventTypeEnum.SPARK_LISTENER_JOB_START.value,
            "job_id": job_id,
            "timestamp": task_time.isoformat().replace("+00:00", "Z"),
            "user": f"user{job_id}@example.com"
        },
        status=LogStatusEnum.PENDING
    )
    logs.append(job_start_log)

    # 2) Multiple Task End logs (1 to 5 tasks)
    num_tasks = random.randint(1, 10)
    for i in range(1, num_tasks + 1):
        task_time = start_time + timedelta(seconds=i * 10)
        task_log = RawLog(
            event=EventTypeEnum.SPARK_LISTENER_TASK_END,
            job_id=job_id,
            user=None,
            timestamp=task_time,
            task_id=f"task_{i:03}",
            log={
                "event": EventTypeEnum.SPARK_LISTENER_TASK_END.value,
                "job_id": job_id,
                "timestamp": task_time.isoformat().replace("+00:00", "Z"),
                "task_id": f"task_{i:03}",
                "duration_ms": random.randint(100, 10000),
                "successful": random.choice([True, False])
            },
            status=LogStatusEnum.PENDING
        )
        logs.append(task_log)

    # 3) Job End log
    job_end_time = start_time + timedelta(seconds=(num_tasks + 1) * 10)
    job_end_log = RawLog(
        event=EventTypeEnum.SPARK_LISTENER_JOB_END,
        job_id=job_id,
        user=None,
        timestamp=job_end_time,
        task_id=None,
        log={
            "event": EventTypeEnum.SPARK_LISTENER_JOB_END.value,
            "job_id": job_id,
            "timestamp": job_end_time.isoformat().replace("+00:00", "Z"),
            "completion_time": job_end_time.isoformat().replace("+00:00", "Z"),
            "job_result": random.choice(["JobSucceeded", "JobFailed"])
        },
        status=LogStatusEnum.PENDING
    )
    logs.append(job_end_log)

    return logs

def insert_sample_jobs():
    session: Session = next(get_db())  # Depends on your DB session setup
    base_time = datetime.now()

    try:
        for job_id in range(1, 11):
            logs = create_job_logs(job_id, base_time + timedelta(minutes=job_id))
            session.add_all(logs)

        session.commit()
        print("Inserted coherent logs for 10 jobs.")

    except SQLAlchemyError as e:
        session.rollback()
        print(f"Database error occurred: {e}")

    except Exception as e:
        session.rollback()
        print(f"Unexpected error occurred: {e}")

    finally:
        session.close()

if __name__ == "__main__":
    insert_sample_jobs()
