from fastapi import FastAPI, Depends, HTTPException, APIRouter, Query, status
import os
from fastapi.responses import FileResponse
from src.handlers import Handler

# Import A2A models
from src.schemas import (
    JSONRPCRequest,
    JSONRPCResponse,
    TaskResult,
    TaskStatus,
    A2AMessage,
    MessagePart,
    Artifact,
)

agent_router = APIRouter()


@agent_router.get("/")
async def root():
    """Health check"""
    return {
        "agent_name": os.getenv("AGENT_NAME"),
        "agent_id": os.getenv("AGENT_ID"),
        "status": "online",
        "protocol": "a2a-jsonrpc-2.0",
    }


@agent_router.get("/image/{image_id}")
async def get_image(image_id: str):
    """Serve generated image"""
    filepath = os.path.join("output", image_id)

    if not os.path.exists(filepath):
        raise HTTPException(status_code=404, detail="Image not found")

    return FileResponse(filepath, media_type="image/png")


# A2A Protocol Endpoint


@agent_router.post("/a2a")
async def a2a_endpoint(request: JSONRPCRequest) -> JSONRPCResponse:
    """Main A2A JSON-RPC 2.0 endpoint"""

    try:
        # Handle message/send method
        if request.method == "message/send":
            return await Handler.handle_message_send(request)

        # Handle execute method
        elif request.method == "execute":
            return await Handler.handle_execute(request)

        else:
            return JSONRPCResponse(
                id=request.id,
                error={
                    "code": -32601,
                    "message": f"Method not found: {request.method}",
                },
            )

    except Exception as e:
        return JSONRPCResponse(
            id=request.id,
            error={"code": -32603, "message": f"Internal error: {str(e)}"},
        )
