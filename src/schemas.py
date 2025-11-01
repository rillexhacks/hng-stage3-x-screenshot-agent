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
    contextId: Optional[str] = None  # ✅ Add this
    metadata: Optional[Dict[str, Any]] = None

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

# ✅ Updated TaskStatus with timestamp
class TaskStatus(BaseModel):
    state: Literal["submitted", "working", "input-required", "completed", "failed", "canceled"]
    timestamp: Optional[str] = Field(default_factory=lambda: datetime.utcnow().isoformat() + "Z")
    message: Optional[A2AMessage] = None

# ✅ Updated Artifact with artifactId and parts structure
class ArtifactPart(BaseModel):
    kind: Literal["text", "file", "data"]
    text: Optional[str] = None
    file_url: Optional[str] = None
    data: Optional[Dict[str, Any]] = None

class Artifact(BaseModel):
    artifactId: str = Field(default_factory=lambda: str(uuid4()))
    name: str
    parts: List[ArtifactPart]  # ✅ Changed from file_url to parts

# ✅ Updated TaskResult with contextId and history
class TaskResult(BaseModel):
    id: str
    contextId: str  # ✅ Add this (required)
    status: TaskStatus
    artifacts: List[Artifact] = []
    history: List[A2AMessage] = []  # ✅ Add this
    kind: Literal["task"] = "task"

class JSONRPCResponse(BaseModel):
    jsonrpc: Literal["2.0"] = "2.0"
    id: str
    result: Optional[TaskResult] = None
    error: Optional[Dict[str, Any]] = None