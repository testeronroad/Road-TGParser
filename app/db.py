from __future__ import annotations

import aiosqlite
from pathlib import Path

from app.config import DB_PATH


SCHEMA = """
CREATE TABLE IF NOT EXISTS channels (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    telegram_id INTEGER NOT NULL UNIQUE,
    title TEXT NOT NULL DEFAULT '',
    description TEXT NOT NULL DEFAULT '',
    members_count INTEGER,
    link TEXT,
    username TEXT,
    category_id TEXT NOT NULL DEFAULT 'other',
    category_name TEXT NOT NULL DEFAULT 'Другое',
    search_keyword TEXT NOT NULL DEFAULT '',
    is_broadcast INTEGER NOT NULL DEFAULT 1,
    parsed_at TEXT NOT NULL DEFAULT (datetime('now'))
);
CREATE INDEX IF NOT EXISTS idx_channels_category ON channels(category_id);
CREATE INDEX IF NOT EXISTS idx_channels_keyword ON channels(search_keyword);
CREATE INDEX IF NOT EXISTS idx_channels_title ON channels(title);
"""


async def get_connection() -> aiosqlite.Connection:
    Path(DB_PATH).parent.mkdir(parents=True, exist_ok=True)
    conn = await aiosqlite.connect(DB_PATH)
    conn.row_factory = aiosqlite.Row
    await conn.executescript(SCHEMA)
    await conn.commit()
    return conn


async def upsert_channel(
    conn: aiosqlite.Connection,
    *,
    telegram_id: int,
    title: str,
    description: str,
    members_count: int | None,
    link: str | None,
    username: str | None,
    category_id: str,
    category_name: str,
    search_keyword: str,
    is_broadcast: bool,
) -> None:
    await conn.execute(
        """
        INSERT INTO channels (
            telegram_id, title, description, members_count, link, username,
            category_id, category_name, search_keyword, is_broadcast, parsed_at
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, datetime('now'))
        ON CONFLICT(telegram_id) DO UPDATE SET
            title = excluded.title,
            description = excluded.description,
            members_count = excluded.members_count,
            link = excluded.link,
            username = excluded.username,
            category_id = excluded.category_id,
            category_name = excluded.category_name,
            search_keyword = excluded.search_keyword,
            is_broadcast = excluded.is_broadcast,
            parsed_at = datetime('now')
        """,
        (
            telegram_id,
            title,
            description,
            members_count,
            link,
            username,
            category_id,
            category_name,
            search_keyword,
            1 if is_broadcast else 0,
        ),
    )
    await conn.commit()


async def list_channels(
    conn: aiosqlite.Connection,
    *,
    q: str | None = None,
    category_id: str | None = None,
    limit: int = 100,
    offset: int = 0,
) -> tuple[list[dict], int]:
    where: list[str] = []
    args: list = []

    if q and q.strip():
        term = f"%{q.strip()}%"
        where.append(
            "(title LIKE ? OR description LIKE ? OR username LIKE ? OR link LIKE ? OR category_name LIKE ? OR search_keyword LIKE ?)"
        )
        args.extend([term] * 6)

    if category_id and category_id != "all":
        where.append("category_id = ?")
        args.append(category_id)

    clause = " AND ".join(where) if where else "1=1"

    cur = await conn.execute(f"SELECT COUNT(*) FROM channels WHERE {clause}", args)
    row = await cur.fetchone()
    total = int(row[0]) if row else 0

    cur = await conn.execute(
        f"""
        SELECT * FROM channels WHERE {clause}
        ORDER BY parsed_at DESC
        LIMIT ? OFFSET ?
        """,
        [*args, limit, offset],
    )
    rows = await cur.fetchall()
    return [dict(r) for r in rows], total


async def list_channels_filtered(
    conn: aiosqlite.Connection,
    *,
    q: str | None = None,
    category_id: str | None = None,
    max_rows: int = 100_000,
) -> list[dict]:
    where: list[str] = []
    args: list = []

    if q and q.strip():
        term = f"%{q.strip()}%"
        where.append(
            "(title LIKE ? OR description LIKE ? OR username LIKE ? OR link LIKE ? OR category_name LIKE ? OR search_keyword LIKE ?)"
        )
        args.extend([term] * 6)

    if category_id and category_id != "all":
        where.append("category_id = ?")
        args.append(category_id)

    clause = " AND ".join(where) if where else "1=1"
    cap = max(1, min(max_rows, 500_000))

    cur = await conn.execute(
        f"""
        SELECT * FROM channels WHERE {clause}
        ORDER BY parsed_at DESC
        LIMIT ?
        """,
        [*args, cap],
    )
    rows = await cur.fetchall()
    return [dict(r) for r in rows]


async def update_channel_category(
    conn: aiosqlite.Connection,
    row_id: int,
    *,
    category_id: str,
    category_name: str,
) -> bool:
    cur = await conn.execute(
        """
        UPDATE channels
        SET category_id = ?, category_name = ?
        WHERE id = ?
        """,
        (category_id, category_name, row_id),
    )
    await conn.commit()
    return cur.rowcount > 0


async def delete_channel_by_id(conn: aiosqlite.Connection, row_id: int) -> bool:
    cur = await conn.execute("DELETE FROM channels WHERE id = ?", (row_id,))
    await conn.commit()
    return cur.rowcount > 0


async def stats_by_category(conn: aiosqlite.Connection) -> list[dict]:
    cur = await conn.execute(
        """
        SELECT category_id, category_name, COUNT(*) AS cnt
        FROM channels
        GROUP BY category_id, category_name
        ORDER BY cnt DESC
        """
    )
    rows = await cur.fetchall()
    return [dict(r) for r in rows]
