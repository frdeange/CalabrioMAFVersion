from pydantic import BaseModel, Field


class ChatRequest(BaseModel):
    message: str = Field(min_length=1)
    bu_id: str | None = None
    conversation_id: str | None = None
    correlation_id: str | None = None


class ChatResponse(BaseModel):
    status: str
    message: str
    intent: str | None = None
    sql: str | None = None
    answer: str | None = None
    conversation_id: str | None = None
    execution_ms: int | None = None
