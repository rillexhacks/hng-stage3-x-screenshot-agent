import os
import json
from typing import Optional
import httpx
import re
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
        """Handle message/send requests (robust latest-text extraction for Telex)."""
        params = request.params
        message = params.message

        # Generate context/task IDs
        context_id = message.contextId or str(uuid.uuid4())
        task_id = message.taskId or str(uuid.uuid4())

        # ---- Robust latest_text() with debug logging ----
        def latest_text(parts):
            """
            Recursively extract candidate texts (in order encountered), clean them,
            ignore noise, and return the last meaningful candidate.
            """
            def is_noise(txt: str) -> bool:
                if not txt:
                    return True
                lower = txt.lower().strip()
                # noise patterns (extend if you see other system lines)
                noise_keywords = [
                    "generating the tweet",
                    "generating the tweet for",
                    "creating the tweet",
                    "creating the verified tweet",
                    "generated twitter screenshot",
                    "generated the tweet",
                    "creating the tweet now",
                    "creating the tweet for",
                ]
                # also ignore very short fragments and pure punctuation
                if len(lower) < 6:
                    return True
                for kw in noise_keywords:
                    if kw in lower:
                        return True
                # ignore code blocks/markup markers
                if lower.startswith("<pre") or lower.startswith("```"):
                    return True
                return False

            def clean_text(raw: str) -> str:
                if raw is None:
                    return ""
                # unescape html entities, remove html tags, normalize whitespace
                un = html.unescape(raw)
                no_tags = re.sub(r"<[^>]+>", "", un)
                # remove leftover &nbsp; etc which html.unescape may leave as non-breaking space
                cleaned = re.sub(r"\s+", " ", no_tags).strip()
                return cleaned

            candidates = []

            def extract(node):
                """Walk node which may be dict, list, or value and collect text candidates."""
                if node is None:
                    return
                # If node is a list: check each item
                if isinstance(node, list):
                    for item in node:
                        extract(item)
                    return
                # If node is a dict: check possible keys
                if isinstance(node, dict):
                    kind = node.get("kind")
                    # direct text
                    if kind == "text" and node.get("text"):
                        txt = clean_text(node.get("text"))
                        candidates.append(txt)
                        return
                    # sometimes Telex wraps text directly in 'text' on a dict without kind
                    if "text" in node and not node.get("kind"):
                        txt = clean_text(node.get("text"))
                        candidates.append(txt)
                    # nested 'data' may be list or dict
                    if node.get("data") is not None:
                        extract(node.get("data"))
                    # sometimes there is a nested 'parts' structure inside data dict
                    if node.get("parts") is not None:
                        extract(node.get("parts"))
                    return
                # other types (string) -> consider directly
                if isinstance(node, str):
                    txt = clean_text(node)
                    candidates.append(txt)
                    return

            # start extraction from top-level parts
            extract(parts)

            # debug log of candidates (won't break production)
            logger.info(f"latest_text candidates (count={len(candidates)}): {candidates!r}")

            # choose the last non-noise candidate
            for cand in reversed(candidates):
                if cand and not is_noise(cand):
                    logger.info(f"latest_text selected: {cand!r}")
                    return cand
            logger.info("latest_text found no non-noise candidate.")
            return ""

       # ---- Extract latest command ----
        # Defensive: message.parts might be missing or None
        parts_val = None
        if hasattr(message, "parts"):
            parts_val = message.parts
        elif isinstance(message, dict) and "parts" in message:
            parts_val = message["parts"]

        # If parts_val is None or empty, try other likely places (fallback)
        if not parts_val:
            # Try to get from params.message directly
            if isinstance(params.message, dict) and "parts" in params.message:
                parts_val = params.message["parts"]
            # some Telex shapes might put text directly under message.text or message.data
            elif isinstance(message, dict) and message.get("text"):
                parts_val = [{"kind": "text", "text": message.get("text")}]
            elif isinstance(message, dict) and message.get("data"):
                parts_val = message.get("data")
            else:
                parts_val = []

        logger.info(f"🔍 DEBUG parts_val type: {type(parts_val)}, length: {len(parts_val) if isinstance(parts_val, list) else 'N/A'}, value preview: {parts_val[:2] if isinstance(parts_val, list) and len(parts_val) > 0 else parts_val}")

        latest_user_text = latest_text(parts_val) or ""
        logger.info(f"🧩 Extracted latest_user_text (raw): {latest_user_text!r}")

        tweet_data = {}
        if latest_user_text:
            # Split by known tweet creation keywords (keep latest)
            split_pattern = r'(?=(?:create|generate|make)\s+(?:a\s+)?(?:verified\s+)?tweet)'
            segments = re.split(split_pattern, latest_user_text, flags=re.IGNORECASE)
            segments = [s.strip() for s in segments if s.strip()]
            logger.info(f"Split segments from latest_user_text: {segments!r}")
            if segments:
                parsed_data = HelperFunctions.parse_tweet_request(segments[-1])
                logger.info(f"parse_tweet_request returned: {parsed_data!r}")
                if parsed_data and "tweet_text" in parsed_data:
                    tweet_data = parsed_data

        # ---- Validate ----
        if "tweet_text" not in tweet_data:
            logger.warning("Missing tweet content after extraction. Returning error.")
            return JSONRPCResponse(
                id=request.id,
                error={
                    "code": -32602,
                    "message": "Missing tweet content. Try: 'create a tweet for john saying hello world'"
                }
            )

        # ---- Prepare data ----
        username = tweet_data.get("username", "user")
        display_name = tweet_data.get("display_name", username.title())
        tweet_text = tweet_data["tweet_text"]
        verified = tweet_data.get("verified", False)
        likes = tweet_data.get("likes", 0)
        retweets = tweet_data.get("retweets", 0)
        replies = tweet_data.get("replies", 0)
        timestamp = tweet_data.get("timestamp", None)

        # ---- Generate screenshot ----
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

        # ---- Store image in Redis ----
        try:
            with open(filepath, "rb") as img_file:
                image_bytes = img_file.read()
                image_base64 = base64.b64encode(image_bytes).decode("utf-8")

            await redis_client.setex(f"image:{image_id}", 86400, image_base64)
            logger.info(f"Stored image in Redis: image:{image_id}")

            os.remove(filepath)
            logger.info(f"Deleted temp file: {filepath}")

        except Exception as e:
            logger.error(f"Failed to store image in Redis: {str(e)}")

        # ---- Store tweet metadata ----
        await redis_client.setex(
            f"tweet:{image_id}",
            86400,
            json.dumps(tweet_data)
        )

        # ---- Create A2A response ----
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

        task_result = TaskResult(
            id=task_id,
            contextId=context_id,
            status=TaskStatus(state="completed", message=response_message),
            artifacts=[artifact],
            history=[]
        )

        return JSONRPCResponse(id=request.id, result=task_result)


    
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