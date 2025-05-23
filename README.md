# Async Spark Event Logs Ingestor & Analyzer

A backend service for ingesting simulated Apache Spark event logs, processing them asynchronously to compute job‑level analytics, and serving those analytics via a REST API with Redis caching and periodic recomputation.

---

## 🚀 Project Overview

1. **Log Ingestor**:

   * `POST /logs/ingest` accepts Spark event logs (`JobStart`, `TaskEnd`, `JobEnd`) and stores them in PostgreSQL (`raw_logs`), marking each as **PENDING**.
   * All timestamps are normalized to UTC.

2. **Background Processing (Celery)**:

   * On ingesting both a `JobStart` and `JobEnd` for the same `job_id`, a Celery task `compute_job_analytics` is triggered to compute:

     * Total duration
     * Task count
     * Failed tasks
     * Success rate
   * Results are upserted into `job_analytics` and source logs marked **PROCESSED**.
   * On each analytics compute, related Redis caches (`job_analytics:<job_id>`, `analytics_summary:<date>`) are invalidated.

3. **Analytics API**:

   * `GET /analytics/jobs/{job_id}`: Returns analytics for a single job. If not yet computed, enqueues a compute task and returns **202 Accepted**. Caches results in Redis (TTL configurable).
   * `GET /analytics/summary?date=YYYY-MM-DD`: Returns analytics for all jobs completed on a given date. Also cached.

4. **Periodic Reconciliation (Celery Beat)**:
   A scheduled task `schedule_pending_analytics` scans the last 2 hours of logs for any jobs with both Start & End but still PENDING entries, enqueues `compute_job_analytics` for them in parallel using a Celery `group`.

5. **Sample Data Script**:
   A standalone Python script generates coherent logs for 10 jobs (1 `JobStart`, 1–10 `TaskEnd`, 1 `JobEnd` each) with UTC timestamps and bulk‑inserts them into PostgreSQL.

---

## 📦 Database Schema

### 1. `raw_logs`

```sql
CREATE TABLE raw_logs (
  id UUID PRIMARY KEY,
  event EVENT_TYPE_ENUM NOT NULL,
  job_id INT NOT NULL,
  "user" TEXT,
  timestamp TIMESTAMPTZ NOT NULL,
  task_id TEXT,
  log JSONB NOT NULL,
  insertion_time TIMESTAMPTZ DEFAULT now(),
  status LOG_STATUS_ENUM NOT NULL DEFAULT 'pending',
  UNIQUE (job_id, event, task_id)
);
```

### 2. `job_analytics`

```sql
CREATE TABLE job_analytics (
  id UUID PRIMARY KEY,
  job_id INT NOT NULL UNIQUE,
  "user" TEXT NOT NULL,
  start_time TIMESTAMPTZ NOT NULL,
  end_time TIMESTAMPTZ NOT NULL,
  duration_seconds INT NOT NULL,
  task_count INT NOT NULL,
  failed_tasks INT NOT NULL,
  success_rate FLOAT NOT NULL,
  insertion_time TIMESTAMPTZ DEFAULT now()
);
```

**Enums**:

* `EventTypeEnum`: `SparkListenerJobStart`, `SparkListenerTaskEnd`, `SparkListenerJobEnd`
* `LogStatusEnum`: `pending`, `processed`

---

## 🛠️ Getting Started

### Prerequisites

* Docker & Docker Compose
* Python 3.12 (for local script)

### Environment Variables (`.env`)

```dotenv
DB_HOST=db
DB_PORT=5432
DB_USER=myuser
DB_PASSWORD=mypassword
DB_NAME=mydb
DATABASE_URL=postgresql+psycopg2://myuser:mypassword@db:5432/mydb
REDIS_URL=redis://redis:6379/0
CACHE_TTL=3600
```

### Run with Docker Compose

```bash
docker-compose up --build
```

* **web**: FastAPI + Uvicorn + Alembic migrations + ingest & analytics API
* **celery**: Celery Worker
* **celery-beat**: Celery Beat scheduler
* **redis**: caching & broker
* **db**: PostgreSQL

---

## 📡 API Endpoints

### 1. Ingest Log

```
POST /logs/ingest
Content-Type: application/json
```

Payload examples:

```json
{ "event": "SparkListenerJobStart", "job_id": 101, "timestamp": "2024-03-30T10:12:45Z", "user":"data_engineer_1" }
```

```json
{ "event": "SparkListenerTaskEnd", "job_id": 101, "timestamp": "2024-03-30T10:13:22Z", "task_id":"task_001","duration_ms":4500,"successful":true }
```

```json
{ "event": "SparkListenerJobEnd", "job_id": 101, "timestamp": "2024-03-30T10:14:03Z","completion_time":"2024-03-30T10:14:03Z","job_result":"JobSucceeded" }
```

### 2. Get Job Analytics

```
GET /analytics/jobs/{job_id}
```

### 3. Get Daily Summary

```
GET /analytics/summary?date=YYYY-MM-DD
```

---

## 🔄 Caching (Redis)

* Single-job results keyed by `job_analytics:{job_id}`
* Daily summary keyed by `analytics_summary:{date}`
* TTL set by `CACHE_TTL` (default 3600s)
* Invalidation on analytics compute for freshness

---

## 🐝 Celery & Beat Schedule

* **Worker** processes `compute_job_analytics(job_id)` tasks in background.
* **Beat** runs `schedule_pending_analytics` every 2 hours (configurable) to backfill missed jobs.
* Uses Celery `group` to enqueue parallel analytics computations.

---

## 📑 Sample Data Script

```bash
python insert_sample_jobs.py
```

* Generates 10 jobs with coherent start/task/end logs in UTC
* Bulk inserts into `raw_logs`

---

