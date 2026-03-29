from __future__ import annotations

import asyncio
from typing import Any

from telethon import TelegramClient, utils
from telethon.errors import FloodWaitError, RPCError
from telethon.tl.functions.channels import GetFullChannelRequest
from telethon.tl.functions.contacts import SearchRequest
from telethon.tl.types import Channel, Chat

from app.config import API_HASH, API_ID, SESSION_PATH

_client: TelegramClient | None = None
_lock = asyncio.Lock()


def _make_client() -> TelegramClient:
    if not API_ID or not API_HASH:
        raise RuntimeError("Задайте API_ID и API_HASH в .env (my.telegram.org)")
    return TelegramClient(SESSION_PATH, API_ID, API_HASH)


async def get_client() -> TelegramClient:
    global _client
    async with _lock:
        if _client is None:
            _client = _make_client()
        if not _client.is_connected():
            await _client.connect()
        if not await _client.is_user_authorized():
            raise RuntimeError(
                "Сессия Telegram не авторизована. Запустите: python login_telegram.py"
            )
        return _client


async def disconnect_client() -> None:
    global _client
    async with _lock:
        if _client and _client.is_connected():
            await _client.disconnect()


def _channel_link(ch: Channel) -> str | None:
    if ch.username:
        return f"https://t.me/{ch.username}"
    if hasattr(ch, "usernames") and ch.usernames:
        u = ch.usernames[0]
        un = getattr(u, "username", None)
        if un:
            return f"https://t.me/{un}"
    return None


async def search_public_chats(keyword: str, limit: int = 30) -> list[dict[str, Any]]:
    keyword = (keyword or "").strip()
    if not keyword:
        return []

    client = await get_client()
    try:
        result = await client(SearchRequest(q=keyword, limit=min(limit, 100)))
    except FloodWaitError as e:
        raise RuntimeError(f"Telegram ограничил запрос. Подождите {e.seconds} сек.") from e
    except RPCError as e:
        raise RuntimeError(f"Ошибка Telegram API: {e}") from e

    out: list[dict[str, Any]] = []
    seen: set[int] = set()

    for chat in result.chats:
        if isinstance(chat, Chat):
            continue
        if not isinstance(chat, Channel):
            continue
        cid = int(utils.get_peer_id(chat))
        if cid in seen:
            continue
        seen.add(cid)

        title = chat.title or ""
        username = getattr(chat, "username", None) or ""
        link = _channel_link(chat)
        description = ""
        members: int | None = None
        try:
            full = await client(GetFullChannelRequest(chat))
            description = (full.full_chat.about or "").strip()
            members = full.full_chat.participants_count
        except (RPCError, ValueError, TypeError):
            pass

        out.append(
            {
                "telegram_id": cid,
                "title": title,
                "description": description,
                "members_count": members,
                "link": link,
                "username": username or None,
                "is_broadcast": bool(chat.broadcast),
                "is_megagroup": bool(chat.megagroup),
            }
        )

    return out
