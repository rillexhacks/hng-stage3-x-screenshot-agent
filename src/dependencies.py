import os
import redis.asyncio as redis
from dotenv import load_dotenv

load_dotenv()

# Determine whether to use REDIS_URL (Upstash) or local Redis
REDIS_URL = os.getenv("REDIS_URL")

if REDIS_URL:
    # Connect using Upstash / cloud Redis URL
    redis_client = redis.from_url(REDIS_URL, decode_responses=True)
else:
    # Connect to local Redis for development
    redis_client = redis.Redis(
        host=os.getenv("REDIS_HOST", "localhost"),
        port=int(os.getenv("REDIS_PORT", 6379)),
        db=int(os.getenv("REDIS_DB", 0)),
        password=os.getenv("REDIS_PASSWORD", None),
        decode_responses=True
    )


