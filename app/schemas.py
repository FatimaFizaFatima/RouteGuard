from typing import Literal, Optional
from pydantic import BaseModel, Field, field_validator

class Message(BaseModel):

    role : Literal['system', 'user', 'assistant']
    content : str

class ChatRequest(BaseModel):

    messages : list[Message] = Field(min_length=1)
    temperature : float = Field(default=0.7, ge=0, le=2)
    max_tokens : Optional[int] = Field(default=None, gt=0)
    task_type : str = "chat"
    @field_validator("task_type")
    @classmethod
    def clean_task_type(cls, value: str) -> str:
        return value.strip().lower()


class Usage(BaseModel):

    input_tokens : int
    output_tokens : int

class GatewayMeta(BaseModel):

    model_used : str
    latency_ms: float
    fallback_used : bool = False
    attempts : list[str] = []
    finish_reason: str | None = None


class ChatResponse(BaseModel):

    id : str
    content : str
    usage : Usage
    gateway : GatewayMeta



