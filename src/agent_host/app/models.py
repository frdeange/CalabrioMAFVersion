from pydantic import BaseModel, Field


class ChatRequest(BaseModel):
    message: str = Field(min_length=1)
    correlation_id: str | None = None


class ChatResponse(BaseModel):
    status: str
    message: str
