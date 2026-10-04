from pydantic import BaseModel, Field


class ChatRequest(BaseModel):
    message: str = Field(min_length=1, max_length=12_000)


class ChatResponse(BaseModel):
    request_id: str
    provider: str
    model: str
    output: str
