from fastapi import FastAPI, HTTPException
import os

from src.router import agent_router as router

from dotenv import load_dotenv



# Load environment variables
load_dotenv()

app = FastAPI(title="Twitter Screenshot Generator Agent")



# Ensure output directory exists
os.makedirs("output", exist_ok=True)

app.include_router(router)


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
