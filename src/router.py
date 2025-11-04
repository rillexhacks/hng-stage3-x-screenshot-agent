from fastapi import FastAPI, Depends, HTTPException, APIRouter, Query, status, Request as request
import os
from fastapi.responses import FileResponse, JSONResponse, Response
from src.handlers import Handler
import json
import base64

import logging

logger = logging.getLogger(__name__)

# Import redis client
from src.dependencies import redis_client  # Adjust this import based on where your redis_client is

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
    logger.info("Health check endpoint called")
    
    response = {
        "agent_name": os.getenv("AGENT_NAME"),
        "agent_id": os.getenv("AGENT_ID"),
        "status": "online",
        "protocol": "a2a-jsonrpc-2.0",
    }
    
    logger.info(f"Health check response: {response}")
    return response


@agent_router.get("/image/{image_id}")
async def get_image(image_id: str):
    """Serve generated tweet images from Redis"""
    
    try:
        logger.info(f"Fetching image: {image_id}")
        
        # Get image data from Redis
        image_data = await redis_client.get(f"image:{image_id}")
        
        if not image_data:
            logger.error(f"Image not found in Redis: {image_id}")
            return JSONResponse(
                status_code=404,
                content={"error": "Image not found"}
            )
        
        # Decode base64 image data
        image_bytes = base64.b64decode(image_data)
        logger.info(f"Image found and decoded: {image_id}")
        
        return Response(
            content=image_bytes,
            media_type="image/png",
            headers={
                "Cache-Control": "public, max-age=86400",  # Cache for 24 hours
                "Content-Disposition": f"inline; filename={image_id}"
            }
        )
        
    except Exception as e:
        logger.error(f"Error serving image {image_id}: {str(e)}", exc_info=True)
        return JSONResponse(
            status_code=500,
            content={"error": f"Failed to serve image: {str(e)}"}
        )


@agent_router.post("/a2a/twitter-screenshot")
async def a2a_endpoint(raw_request: request):
    """Main A2A JSON-RPC 2.0 endpoint - with debug logging"""
    
    # Get raw body
    try:
        body = await raw_request.body()
        logger.info(f"Raw body bytes: {body}")
        
        # Parse JSON
        json_body = json.loads(body)
        logger.info(f"Parsed JSON: {json.dumps(json_body, indent=2)}")
        
    except Exception as e:
        logger.error(f"Failed to read/parse body: {str(e)}", exc_info=True)
        return JSONResponse(
            status_code=200,
            content={
                "jsonrpc": "2.0",
                "id": "unknown",
                "error": {"code": -32700, "message": f"Parse error: {str(e)}"}
            }
        )
    
    # Try to validate with Pydantic
    try:
        request = JSONRPCRequest(**json_body)
        logger.info("Pydantic validation SUCCESS")
        
        # Handle message/send method
        if request.method == "message/send":
            logger.info("Handling message/send")
            result = await Handler.handle_message_send(request)
            return JSONResponse(status_code=200, content=result.model_dump())

        # Handle execute method
        elif request.method == "execute":
            logger.info("Handling execute")
            result = await Handler.handle_execute(request)
            return JSONResponse(status_code=200, content=result.model_dump())

        else:
            logger.warning(f"Method not found: {request.method}")
            return JSONResponse(
                status_code=200,
                content={
                    "jsonrpc": "2.0",
                    "id": request.id,
                    "error": {
                        "code": -32601,
                        "message": f"Method not found: {request.method}"
                    }
                }
            )

    except Exception as e:
        logger.error(f"Pydantic validation FAILED: {str(e)}", exc_info=True)
        logger.error(f"Request body structure: {json.dumps(json_body, indent=2)}")
        
        # Return a valid error response
        return JSONResponse(
            status_code=200,
            content={
                "jsonrpc": "2.0",
                "id": json_body.get("id", "unknown"),
                "error": {
                    "code": -32602,
                    "message": f"Invalid params: {str(e)}"
                }
            }
        )