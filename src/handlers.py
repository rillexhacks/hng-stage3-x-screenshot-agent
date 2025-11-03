import os
import json
from typing import Optional
import httpx

from src.dependencies import redis_client
from src.utils import HelperFunctions
import uuid
import logging

logger = logging.getLogger(__name__)

from src.schemas import (
    ArtifactPart,
    JSONRPCRequest,
    JSONRPCResponse,
    TaskResult,
    TaskStatus,
    A2AMessage,
    MessagePart,
    Artifact
)


class Handler:
   
    @staticmethod
    async def handle_message_send(request: JSONRPCRequest) -> JSONRPCResponse:
        """Handle message/send requests"""
        
        params = request.params
        message = params.message
        
        # Get or generate contextId
        context_id = message.contextId or str(uuid.uuid4())
        task_id = message.taskId or str(uuid.uuid4())
        
        # Extract tweet data from message parts
        tweet_data = {}
        user_text = ""
        
        for part in message.parts:
            if part.kind == "text" and part.text:
                user_text = part.text
                if not part.text.startswith("<"):
                    parsed_data = HelperFunctions.parse_tweet_request(part.text)
                    if parsed_data:
                        tweet_data.update(parsed_data)
            
            elif part.kind == "data" and part.data:
                if isinstance(part.data, dict):
                    tweet_data.update(part.data)
                elif isinstance(part.data, list):
                    for item in reversed(part.data):
                        if isinstance(item, dict) and item.get("kind") == "text":
                            text = item.get("text", "")
                            if not text.startswith("<") and not any(skip in text.lower() for skip in ["generating", "creating"]):
                                parsed = HelperFunctions.parse_tweet_request(text)
                                if parsed and "tweet_text" in parsed:
                                    tweet_data.update(parsed)
                                    break
        
        # Validate required fields
        if "tweet_text" not in tweet_data:
            return JSONRPCResponse(
                id=request.id,
                error={
                    "code": -32602,
                    "message": "Missing tweet content. Try: 'create a tweet for john saying hello world'"
                }
            )
        
        # Set defaults
        username = tweet_data.get("username", "user")
        display_name = tweet_data.get("display_name", username.title())
        tweet_text = tweet_data["tweet_text"]
        verified = tweet_data.get("verified", False)
        likes = tweet_data.get("likes", 0)
        retweets = tweet_data.get("retweets", 0)
        replies = tweet_data.get("replies", 0)
        timestamp = tweet_data.get("timestamp", None)
        
        # Generate screenshot
        filepath = HelperFunctions.generate_tweet_screenshot(
            username=username,
            display_name=display_name,
            tweet_text=tweet_text,
            verified=verified,
            likes=likes,
            retweets=retweets,
            replies=replies,
            timestamp=timestamp
        )
        
        image_id = os.path.basename(filepath)
        image_url = f"{os.getenv('AGENT_URL')}/image/{image_id}"
        
        # Store image in Redis
        import base64
        try:
            with open(filepath, "rb") as img_file:
                image_bytes = img_file.read()
                image_base64 = base64.b64encode(image_bytes).decode('utf-8')
            
            await redis_client.setex(
                f"image:{image_id}",
                86400,
                image_base64
            )
            logger.info(f"Stored image in Redis: image:{image_id}")
            
            os.remove(filepath)
            logger.info(f"Deleted temp file: {filepath}")
            
        except Exception as e:
            logger.error(f"Failed to store image in Redis: {str(e)}")
        
        # Store tweet metadata
        await redis_client.setex(
            f"tweet:{image_id}",
            86400,
            json.dumps(tweet_data)
        )
        
        # Create response message - TEXT ONLY with embedded image
        response_message = A2AMessage(
            role="agent",
            parts=[
                MessagePart(
                    kind="text",
                    text=f"Generated Twitter screenshot for @{username}\n\n![Tweet Screenshot]({image_url})\n\nView image: {image_url}"
                )
            ],
            taskId=task_id,
            contextId=context_id
        )
        
        # Create artifact - TEXT ONLY with embedded image
        artifact = Artifact(
            name=f"twitter_screenshot_{username}.png",
            mimeType="image/png",
            parts=[
                ArtifactPart(
                    kind="text",
                    text=f"Generated Twitter screenshot for @{username}\n\n![Tweet Screenshot]({image_url})\n\nView image: {image_url}"
                )
            ]
        )
        
        # Create task result
        task_result = TaskResult(
            id=task_id,
            contextId=context_id,
            status=TaskStatus(
                state="completed",
                message=response_message
            ),
            artifacts=[artifact],
            history=[]
        )
        
        return JSONRPCResponse(
            id=request.id,
            result=task_result
        )
    
    @staticmethod
    async def handle_execute(request: JSONRPCRequest) -> JSONRPCResponse:
        """Handle execute requests (batch processing)"""
        
        params = request.params
        messages = params.messages
        
        context_id = params.contextId or str(uuid.uuid4())
        task_id = params.taskId or str(uuid.uuid4())
        
        all_artifacts = []
        all_history = []
        last_message = None
        
        for message in messages:
            tweet_data = {}
            
            for part in message.parts:
                if part.kind == "text":
                    parsed_data = HelperFunctions.parse_tweet_request(part.text)
                    tweet_data.update(parsed_data)
                elif part.kind == "data" and part.data:
                    tweet_data.update(part.data)
            
            if "tweet_text" not in tweet_data:
                continue
            
            username = tweet_data.get("username", "user")
            display_name = tweet_data.get("display_name", username.title())
            
            filepath = HelperFunctions.generate_tweet_screenshot(
                username=username,
                display_name=display_name,
                tweet_text=tweet_data["tweet_text"],
                verified=tweet_data.get("verified", False),
                likes=tweet_data.get("likes", 0),
                retweets=tweet_data.get("retweets", 0),
                replies=tweet_data.get("replies", 0),
                timestamp=tweet_data.get("timestamp", None)
            )
            
            image_id = os.path.basename(filepath)
            image_url = f"{os.getenv('AGENT_URL')}/image/{image_id}"
            
            # TEXT ONLY artifact
            artifact = Artifact(
                name=f"twitter_screenshot_{username}.png",
                mimeType="image/png",
                parts=[
                    ArtifactPart(
                        kind="text",
                        text=f"Generated screenshot for @{username}\n\n![Tweet Screenshot]({image_url})\n\nView image: {image_url}"
                    )
                ]
            )
            all_artifacts.append(artifact)
            
            # TEXT ONLY message
            response_message = A2AMessage(
                role="agent",
                parts=[
                    MessagePart(
                        kind="text",
                        text=f"Generated screenshot for @{username}\n\n![Tweet Screenshot]({image_url})\n\nView image: {image_url}"
                    )
                ],
                taskId=task_id,
                contextId=context_id
            )
            
            last_message = response_message
            all_history.append(response_message)
        
        task_result = TaskResult(
            id=task_id,
            contextId=context_id,
            status=TaskStatus(
                state="completed",
                message=last_message
            ),
            artifacts=all_artifacts,
            history=all_history
        )
        
        return JSONRPCResponse(
            id=request.id,
            result=task_result
        )