
from pydantic import BaseModel, Field
from typing import Literal, Optional, List, Dict, Any
from datetime import datetime
from uuid import uuid4

class MessagePart(BaseModel):
    kind: Literal["text", "data", "file"]
    text: Optional[str] = None
    data: Optional[Dict[str, Any]] = None
    file_url: Optional[str] = None

class A2AMessage(BaseModel):
    kind: Literal["message"] = "message"
    role: Literal["user", "agent", "system"]
    parts: List[MessagePart]
    messageId: str = Field(default_factory=lambda: str(uuid4()))
    taskId: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = None

# Simplified configuration without push notifications
class MessageConfiguration(BaseModel):
    blocking: bool = True
    acceptedOutputModes: List[str] = ["text/plain", "image/png", "image/svg+xml"]

class MessageParams(BaseModel):
    message: A2AMessage
    configuration: MessageConfiguration = Field(default_factory=MessageConfiguration)

class ExecuteParams(BaseModel):
    contextId: Optional[str] = None
    taskId: Optional[str] = None
    messages: List[A2AMessage]

class JSONRPCRequest(BaseModel):
    jsonrpc: Literal["2.0"]
    id: str
    method: Literal["message/send", "execute"]
    params: MessageParams | ExecuteParams

# Simplified task status
class TaskStatus(BaseModel):
    state: Literal["working", "completed", "failed"]
    message: Optional[A2AMessage] = None

# Simplified artifact - just name and file URL
class Artifact(BaseModel):
    name: str
    file_url: str

# Simplified task result
class TaskResult(BaseModel):
    id: str
    status: TaskStatus
    artifacts: List[Artifact] = []
    kind: Literal["task"] = "task"

class JSONRPCResponse(BaseModel):
    jsonrpc: Literal["2.0"] = "2.0"
    id: str
    result: Optional[TaskResult] = None
    error: Optional[Dict[str, Any]] = None