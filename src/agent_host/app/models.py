from typing import Any

from pydantic import BaseModel, ConfigDict, Field, field_validator


class ChatRequest(BaseModel):
    message: str = Field(min_length=1, max_length=4000)
    bu_id: str | None = None
    conversation_id: str | None = None
    correlation_id: str | None = None

    @field_validator("message")
    @classmethod
    def validate_message_not_whitespace(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("message must not be blank")
        return value


class ChatResponse(BaseModel):
    status: str
    message: str
    error: str | None = None
    intent: str | None = None
    sql: str | None = None
    answer: str | None = None
    conversation_id: str | None = None
    execution_ms: int | None = None


class WorkflowEventResponse(BaseModel):
    model_config = ConfigDict(extra="allow")

    event: str | None = None
    stage: str | None = None
    status: str | None = None
    message: str | None = None
    conversation_id: str | None = None
    payload: dict[str, Any] | None = None
    error: str | None = None
