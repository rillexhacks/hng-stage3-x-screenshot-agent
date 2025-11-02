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

    async def send_webhook_notification(webhook_url: str, task_result: TaskResult, token: Optional[str] = None):
        """Send task result to Telex webhook"""
        
        headers = {"Content-Type": "application/json"}
        if token:
            headers["Authorization"] = f"Bearer {token}"
        
        payload = {
            "jsonrpc": "2.0",
            "method": "task/update",
            "params": task_result.model_dump()
        }
        
        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.post(webhook_url, json=payload, headers=headers)
                logger.info(f"✅ Webhook sent - Status: {response.status_code}")
                logger.info(f"Webhook response: {response.text}")
        except Exception as e:
            logger.error(f"❌ Failed to send webhook: {str(e)}")


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
                # ✅ Parse only if it looks like a real request (not HTML)
                if not part.text.startswith("<"):  # Skip HTML content
                    parsed_data = HelperFunctions.parse_tweet_request(part.text)
                    if parsed_data:  # Only update if we got valid data
                        tweet_data.update(parsed_data)
            
            elif part.kind == "data" and part.data:
                if isinstance(part.data, dict):
                    tweet_data.update(part.data)
                elif isinstance(part.data, list):
                    # ✅ Get the LAST non-HTML text from conversation history
                    for item in reversed(part.data):
                        if isinstance(item, dict) and item.get("kind") == "text":
                            text = item.get("text", "")
                            # Skip HTML and bot responses
                            if not text.startswith("<") and not any(skip in text.lower() for skip in ["generating", "creating"]):
                                parsed = HelperFunctions.parse_tweet_request(text)
                                if parsed and "tweet_text" in parsed:
                                    tweet_data.update(parsed)
                                    break  # Use only the most recent valid request
        
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
            # Read the generated image file
            with open(filepath, "rb") as img_file:
                image_bytes = img_file.read()
                image_base64 = base64.b64encode(image_bytes).decode('utf-8')
            
            # Store the IMAGE in Redis (different key from metadata)
            await redis_client.setex(
                f"image:{image_id}",  # This is what /image/{image_id} endpoint looks for
                86400,  # 24 hours
                image_base64
            )
            logger.info(f"✅ Stored image in Redis: image:{image_id}")
            
            # Clean up the temporary file from disk
            os.remove(filepath)
            logger.info(f"✅ Deleted temp file: {filepath}")
            
        except Exception as e:
            logger.error(f"❌ Failed to store image in Redis: {str(e)}")
        
        # Store tweet METADATA in Redis (24 hours)
        await redis_client.setex(
            f"tweet:{image_id}",
            86400,
            json.dumps(tweet_data)
        )
        
        # Create response message
        response_message = A2AMessage(
            role="agent",
            parts=[
                MessagePart(
                    kind="text",
                    text=f"Generated Twitter screenshot for @{username}"
                ),
                MessagePart(
                    kind="file",
                    file_url=image_url
                )
            ],
            taskId=task_id,
            contextId=context_id
        )
        
        # Create artifact
        artifact = Artifact(
            name=f"twitter_screenshot_{username}.png",
            parts=[
                ArtifactPart(
                    kind="file",
                    file_url=image_url
                )
            ]
        )
        
        # Create task result
        task_result = TaskResult(
            id=task_id,
            contextId=context_id,
            status=TaskStatus(
                state="input-required",
                message=response_message
            ),
            artifacts=[artifact],
            history=[]
        )
        
        # ✅✅✅ WEBHOOK NOTIFICATION SUPPORT ✅✅✅
        try:
            configuration = params.configuration
            push_config = configuration.pushNotificationConfig
            
            if push_config and push_config.get('url'):
                webhook_url = push_config['url']
                token = push_config.get('token')
                logger.info(f"📤 Sending webhook notification to: {webhook_url}")
                
                # Send webhook notification
                await Handler.send_webhook_notification(webhook_url, task_result, token)
        except Exception as e:
            logger.error(f"❌ Webhook notification error: {str(e)}")
        # ✅✅✅ END WEBHOOK SUPPORT ✅✅✅
        
        return JSONRPCResponse(
            id=request.id,
            result=task_result
        )
    @staticmethod
    async def handle_execute(request: JSONRPCRequest) -> JSONRPCResponse:
        """Handle execute requests (batch processing)"""
        
        params = request.params
        messages = params.messages
        
        # Get or generate contextId
        context_id = params.contextId or str(uuid.uuid4())
        task_id = params.taskId or str(uuid.uuid4())
        
        # Process all messages
        all_artifacts = []
        all_history = []
        last_message = None
        
        for message in messages:
            # Extract tweet data
            tweet_data = {}
            
            for part in message.parts:
                if part.kind == "text":
                    # Parse natural language
                    parsed_data = HelperFunctions.parse_tweet_request(part.text)
                    tweet_data.update(parsed_data)
                elif part.kind == "data" and part.data:
                    tweet_data.update(part.data)
            
            if "tweet_text" not in tweet_data:
                continue
            
            # Set defaults
            username = tweet_data.get("username", "user")
            display_name = tweet_data.get("display_name", username.title())
            
            # Generate screenshot
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
            
            # Create artifact
            artifact = Artifact(
                name=f"twitter_screenshot_{username}.png",
                parts=[
                    ArtifactPart(
                        kind="file",
                        file_url=image_url
                    )
                ]
            )
            all_artifacts.append(artifact)
            
            # Create response message
            response_message = A2AMessage(
                role="agent",
                parts=[
                    MessagePart(
                        kind="text",
                        text=f"Generated screenshot for @{username}"
                    ),
                    MessagePart(
                        kind="file",
                        file_url=image_url
                    )
                ],
                taskId=task_id,
                contextId=context_id
            )
            
            last_message = response_message
            all_history.append(response_message)
        
        # Create task result
        task_result = TaskResult(
            id=task_id,
            contextId=context_id,
            status=TaskStatus(
                state="input-required",
                message=last_message
            ),
            artifacts=all_artifacts,
            history=all_history
        )
        
        return JSONRPCResponse(
            id=request.id,
            result=task_result
        )
