import dotenv
import os

dotenv.load_dotenv()


REDIS_URL= os.getenv("REDIS_URL",None)
CELERY_BROKER_URL= REDIS_URL
CELERY_RESULT_BACKEND= REDIS_URL

#Postgres Connection Details
if os.getenv("IN_DOCKER") != "1":
  DB_HOST="localhost"
else:
  DB_HOST=os.environ.get("DB_HOST","db")
DB_PORT = os.getenv("DB_PORT","5432")
DB_USER = os.getenv("DB_USER","postgres")
DB_PASSWORD = os.getenv("DB_PASSWORD","postgres")
DB_NAME = os.getenv("DB_NAME","postgres")
DATABASE_URL= f"postgresql://{DB_USER}:{DB_PASSWORD}@{DB_HOST}:{DB_PORT}/{DB_NAME}"

#Redis Connection Details
REDIS_HOST = os.getenv("REDIS_HOST","localhost")
REDIS_PORT = os.getenv("REDIS_PORT","6379")
REDIS_DB = os.getenv("REDIS_DB","0")

CACHING_TTL=3600 # 1 hour
SCHEDULER_TIMEOUT=60 # 1 minute