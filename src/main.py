from fastapi import FastAPI, HTTPException
import os
import logging

from src.router import agent_router as router

from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# ✅ Configure logging properly
log_level = os.getenv("LOG_LEVEL", "INFO").upper()
log_format = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"

# Ensure logs directory exists
os.makedirs("logs", exist_ok=True)

# Configure root logger
logging.basicConfig(
    level=getattr(logging, log_level, logging.INFO),
    format=log_format,
    handlers=[
        logging.StreamHandler(),  # Console output
        logging.FileHandler("logs/app.log", mode="a"),  # File output
    ],
)

# Create logger for main module
logger = logging.getLogger(__name__)
logger.info("Starting Twitter Screenshot Generator Agent")

app = FastAPI(title="Twitter Screenshot Generator Agent")


# Ensure output directory exists
os.makedirs("output", exist_ok=True)
logger.info("Output directory created/verified")

app.include_router(router)
logger.info("Router included successfully")


@app.on_event("startup")
async def startup_event():
    logger.info("FastAPI application started successfully")


@app.on_event("shutdown")
async def shutdown_event():
    logger.info("FastAPI application shutting down")


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8000, log_level="info")
