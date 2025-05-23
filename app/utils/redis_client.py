import redis
from app.utils.config import REDIS_HOST,REDIS_DB,REDIS_PORT

redis_client = redis.Redis(
    host=REDIS_HOST,
    port=REDIS_PORT,
    db=REDIS_DB,
)