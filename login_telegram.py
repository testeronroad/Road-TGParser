from __future__ import annotations

import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from dotenv import load_dotenv

load_dotenv()

from telethon import TelegramClient

from app.config import API_HASH, API_ID, SESSION_PATH


async def main() -> None:
    if not API_ID or not API_HASH:
        print("Скопируйте .env.example в .env и укажите API_ID и API_HASH.")
        sys.exit(1)

    Path(SESSION_PATH).parent.mkdir(parents=True, exist_ok=True)
    client = TelegramClient(SESSION_PATH, API_ID, API_HASH)
    await client.start()
    me = await client.get_me()
    print(f"Успешно: {me.first_name} (@{me.username or 'без username'})")
    await client.disconnect()


if __name__ == "__main__":
    asyncio.run(main())
