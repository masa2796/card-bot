from typing import List, Literal, Optional

from pydantic import BaseModel, Field


class ChatMessage(BaseModel):
    role: Literal["user", "assistant"]
    content: str


class ChatRequest(BaseModel):
    message: str
    history: Optional[List[ChatMessage]] = None


class ChatResponseMeta(BaseModel):
    used_context_count: int
    matched_titles: List[str] = Field(default_factory=list)
    used_namespace: Optional[str] = None
    fallback_namespace: Optional[str] = None
    raw_match_count: Optional[int] = None
    upstash_status_code: Optional[int] = None
    upstash_error: Optional[str] = None


class ChatResponse(BaseModel):
    answer: str
    meta: ChatResponseMeta
