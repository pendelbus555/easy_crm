from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class UserRead(BaseModel):
    id: int
    telegram_user_id: int | None
    username: str | None
    first_name: str | None
    last_name: str | None

    model_config = ConfigDict(from_attributes=True)


class MessageRead(BaseModel):
    id: int
    chat_id: int
    direction: str
    text: str
    telegram_message_id: int | None
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class ChatRead(BaseModel):
    id: int
    telegram_chat_id: int
    title: str | None
    user: UserRead | None
    last_message: MessageRead | None = None
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class SendMessageRequest(BaseModel):
    chat_id: int = Field(..., description="Internal CRM chat id")
    text: str = Field(..., min_length=1, max_length=4096)


class SendMessageResponse(BaseModel):
    message: MessageRead
