from typing import List, Literal, Optional

from pydantic import BaseModel, Field


class ChatMessage(BaseModel):
    role: Literal["user", "assistant"]
    content: str


class ChatRequest(BaseModel):
    message: str
    history: Optional[List[ChatMessage]] = None


class CardSummary(BaseModel):
    model_config = {"populate_by_name": True}
    card_id: str
    name: str
    class_: str = Field(alias="class")
    rarity: str
    cost: int
    attack: int
    hp: int
    effect: str
    keywords: List[str] = Field(default_factory=list)
    image_before: str
    image_after: str


class ChatResponseMeta(BaseModel):
    used_context_count: int
    matched_titles: List[str] = Field(default_factory=list)
    used_namespace: Optional[str] = None
    fallback_namespace: Optional[str] = None
    raw_match_count: Optional[int] = None
    upstash_status_code: Optional[int] = None
    upstash_error: Optional[str] = None
    cards: List[CardSummary] = Field(default_factory=list)


class ChatResponse(BaseModel):
    answer: str
    meta: ChatResponseMeta
