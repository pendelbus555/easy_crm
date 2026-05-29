from contextlib import asynccontextmanager
from datetime import UTC, datetime
from typing import Annotated

from fastapi import Depends, FastAPI, HTTPException, Request, WebSocket, WebSocketDisconnect, status
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.config import get_settings
from app.database import get_session, init_db
from app.models import Chat, Message, MessageDirection
from app.schemas import ChatRead, MessageRead, SendMessageRequest, SendMessageResponse
from app.telegram import (
    close_bot_session,
    feed_telegram_update,
    get_bot,
    serialize_chat,
    serialize_message,
    setup_webhook,
)
from app.websocket import manager

settings = get_settings()
SessionDep = Annotated[AsyncSession, Depends(get_session)]


@asynccontextmanager
async def lifespan(_: FastAPI):
    await init_db()
    await setup_webhook()
    yield
    await close_bot_session()


app = FastAPI(title="Telegram CRM MVP", version="0.1.0", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[settings.frontend_origin, "http://localhost:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/")
async def root() -> dict[str, str]:
    return {"status": "ok", "service": "telegram-crm-backend"}


@app.get("/health")
async def health() -> dict[str, str]:
    return {"status": "ok"}


@app.get("/chats", response_model=list[ChatRead])
async def get_chats(session: SessionDep) -> list[dict]:
    result = await session.execute(
        select(Chat)
        .options(selectinload(Chat.user))
        .order_by(Chat.updated_at.desc(), Chat.id.desc())
    )
    chats = result.scalars().all()

    response: list[dict] = []
    for chat in chats:
        last_message = await get_last_message(session, chat.id)
        response.append(serialize_chat(chat, last_message))

    return response


@app.get("/messages/{chat_id}", response_model=list[MessageRead])
async def get_messages(chat_id: int, session: SessionDep) -> list[Message]:
    chat = await session.get(Chat, chat_id)
    if chat is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Chat not found")

    result = await session.execute(
        select(Message)
        .where(Message.chat_id == chat_id)
        .order_by(Message.created_at.asc(), Message.id.asc())
    )
    return list(result.scalars().all())


@app.post("/send-message", response_model=SendMessageResponse)
async def send_message(payload: SendMessageRequest, session: SessionDep) -> dict:
    result = await session.execute(
        select(Chat)
        .where(Chat.id == payload.chat_id)
        .options(selectinload(Chat.user))
    )
    chat = result.scalar_one_or_none()
    if chat is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Chat not found")

    bot = get_bot()
    if bot is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Telegram bot token is not configured",
        )

    sent_message = await bot.send_message(chat_id=chat.telegram_chat_id, text=payload.text)
    message = Message(
        chat_id=chat.id,
        direction=MessageDirection.outgoing,
        text=payload.text,
        telegram_message_id=sent_message.message_id,
    )
    chat.updated_at = datetime.now(UTC)
    session.add(message)
    await session.commit()
    await session.refresh(message)

    message_payload = serialize_message(message)
    await manager.broadcast(
        "message_created",
        {
            "chat": serialize_chat(chat, message),
            "message": message_payload,
        },
    )

    return {"message": message_payload}


@app.post("/telegram/webhook")
async def telegram_webhook(request: Request) -> dict[str, bool]:
    secret = request.headers.get("x-telegram-bot-api-secret-token")
    if settings.telegram_webhook_secret and secret != settings.telegram_webhook_secret:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Invalid webhook secret")

    await feed_telegram_update(await request.json())
    return {"ok": True}


@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket) -> None:
    await manager.connect(websocket)
    try:
        while True:
            await websocket.receive_text()
    except WebSocketDisconnect:
        manager.disconnect(websocket)


async def get_last_message(session: AsyncSession, chat_id: int) -> Message | None:
    result = await session.execute(
        select(Message)
        .where(Message.chat_id == chat_id)
        .order_by(Message.created_at.desc(), Message.id.desc())
        .limit(1)
    )
    return result.scalar_one_or_none()
