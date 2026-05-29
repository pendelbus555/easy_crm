from datetime import UTC, datetime

from aiogram import Bot, Dispatcher
from aiogram.types import Message as TelegramMessage, Update
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import get_settings
from app.database import async_session
from app.models import Chat, Message, MessageDirection, User
from app.websocket import manager

settings = get_settings()
dp = Dispatcher()
_bot: Bot | None = None


def get_bot() -> Bot | None:
    global _bot

    token = settings.telegram_bot_token
    if not token or token == "replace_me":
        return None

    if _bot is None:
        _bot = Bot(token=token)
    return _bot


async def setup_webhook() -> None:
    bot = get_bot()
    if not bot or not settings.telegram_webhook_url:
        return

    await bot.set_webhook(
        url=settings.telegram_webhook_url,
        secret_token=settings.telegram_webhook_secret,
        drop_pending_updates=False,
    )


async def close_bot_session() -> None:
    if _bot is not None:
        await _bot.session.close()


async def feed_telegram_update(payload: dict) -> None:
    bot = get_bot()
    if bot is None:
        raise RuntimeError("Telegram bot token is not configured")

    update = Update.model_validate(payload, context={"bot": bot})
    await dp.feed_update(bot, update)


@dp.message()
async def handle_incoming_message(telegram_message: TelegramMessage) -> None:
    text = telegram_message.text or telegram_message.caption
    if not text:
        return

    async with async_session() as session:
        chat, message = await save_incoming_message(session, telegram_message, text)
        await manager.broadcast(
            "message_created",
            {
                "chat": serialize_chat(chat, message),
                "message": serialize_message(message),
            },
        )


async def save_incoming_message(
    session: AsyncSession,
    telegram_message: TelegramMessage,
    text: str,
) -> tuple[Chat, Message]:
    user = await upsert_user(session, telegram_message)
    chat = await upsert_chat(session, telegram_message, user)

    message = Message(
        chat_id=chat.id,
        direction=MessageDirection.incoming,
        text=text,
        telegram_message_id=telegram_message.message_id,
    )
    chat.updated_at = datetime.now(UTC)
    session.add(message)
    await session.commit()
    await session.refresh(message)

    return chat, message


async def upsert_user(session: AsyncSession, telegram_message: TelegramMessage) -> User | None:
    telegram_user = telegram_message.from_user
    if telegram_user is None:
        return None

    result = await session.execute(select(User).where(User.telegram_user_id == telegram_user.id))
    user = result.scalar_one_or_none()

    if user is None:
        user = User(telegram_user_id=telegram_user.id)
        session.add(user)

    user.username = telegram_user.username
    user.first_name = telegram_user.first_name
    user.last_name = telegram_user.last_name

    await session.flush()
    return user


async def upsert_chat(
    session: AsyncSession,
    telegram_message: TelegramMessage,
    user: User | None,
) -> Chat:
    result = await session.execute(
        select(Chat).where(Chat.telegram_chat_id == telegram_message.chat.id)
    )
    chat = result.scalar_one_or_none()

    if chat is None:
        chat = Chat(telegram_chat_id=telegram_message.chat.id)
        session.add(chat)

    chat.title = build_chat_title(telegram_message)
    chat.user_id = user.id if user else None
    chat.user = user
    chat.updated_at = datetime.now(UTC)

    await session.flush()
    return chat


def build_chat_title(telegram_message: TelegramMessage) -> str:
    telegram_chat = telegram_message.chat
    name_parts = [telegram_chat.first_name, telegram_chat.last_name]
    full_name = " ".join(part for part in name_parts if part)

    return (
        telegram_chat.title
        or full_name
        or telegram_chat.username
        or f"Telegram chat {telegram_chat.id}"
    )


def serialize_user(user: User | None) -> dict | None:
    if user is None:
        return None

    return {
        "id": user.id,
        "telegram_user_id": user.telegram_user_id,
        "username": user.username,
        "first_name": user.first_name,
        "last_name": user.last_name,
    }


def serialize_message(message: Message) -> dict:
    return {
        "id": message.id,
        "chat_id": message.chat_id,
        "direction": message.direction,
        "text": message.text,
        "telegram_message_id": message.telegram_message_id,
        "created_at": message.created_at,
    }


def serialize_chat(chat: Chat, last_message: Message | None = None) -> dict:
    return {
        "id": chat.id,
        "telegram_chat_id": chat.telegram_chat_id,
        "title": chat.title,
        "user": serialize_user(chat.user),
        "last_message": serialize_message(last_message) if last_message else None,
        "created_at": chat.created_at,
        "updated_at": chat.updated_at,
    }
