from __future__ import annotations

import asyncio
from contextlib import asynccontextmanager
from pathlib import Path

from datetime import datetime, timezone

from fastapi import FastAPI, HTTPException, Query
from fastapi.responses import FileResponse, Response
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

from app import categorizer
from app import db as database
from app import export_io
from app import telegram_service

STATIC_DIR = Path(__file__).resolve().parent / "static"


@asynccontextmanager
async def lifespan(app: FastAPI):
    yield
    await telegram_service.disconnect_client()


app = FastAPI(
    title="RoadParser",
    description="Каталог публичных каналов и супергрупп Telegram. Road Soft.",
    lifespan=lifespan,
)

if STATIC_DIR.is_dir():
    app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")


class ParseRequest(BaseModel):
    keyword: str = Field(..., min_length=1, max_length=200)
    limit: int = Field(30, ge=1, le=100)


class ParseResponse(BaseModel):
    saved: int
    items: list[dict]
    errors: list[str] = []


class ChannelCategoryPatch(BaseModel):
    category_id: str = Field(..., min_length=1, max_length=64)


@app.get("/")
async def index():
    index_path = STATIC_DIR / "index.html"
    if not index_path.is_file():
        raise HTTPException(404, "Frontend не найден")
    return FileResponse(index_path)


@app.get("/api/health")
async def health():
    conn = await database.get_connection()
    await conn.close()
    tg_ok = False
    tg_message = ""
    try:
        c = await telegram_service.get_client()
        tg_ok = await c.is_user_authorized()
    except Exception as e:
        tg_message = str(e)
    return {
        "database": "ok",
        "telegram_authorized": tg_ok,
        "telegram_message": tg_message or None,
    }


@app.get("/api/categories")
async def categories():
    return {"categories": categorizer.all_categories()}


@app.post("/api/parse", response_model=ParseResponse)
async def parse_channels(body: ParseRequest):
    errors: list[str] = []
    try:
        raw = await telegram_service.search_public_chats(body.keyword, body.limit)
    except RuntimeError as e:
        raise HTTPException(503, detail=str(e)) from e

    conn = await database.get_connection()
    saved = 0
    items: list[dict] = []
    try:
        for row in raw:
            cat_id, cat_name = categorizer.classify(row["title"], row["description"])
            await database.upsert_channel(
                conn,
                telegram_id=row["telegram_id"],
                title=row["title"],
                description=row["description"],
                members_count=row["members_count"],
                link=row["link"],
                username=row["username"],
                category_id=cat_id,
                category_name=cat_name,
                search_keyword=body.keyword.strip(),
                is_broadcast=row["is_broadcast"] and not row["is_megagroup"],
            )
            saved += 1
            items.append(
                {
                    **row,
                    "category_id": cat_id,
                    "category_name": cat_name,
                    "search_keyword": body.keyword.strip(),
                }
            )
            await asyncio.sleep(0.05)
    finally:
        await conn.close()

    return ParseResponse(saved=saved, items=items, errors=errors)


@app.get("/api/channels")
async def get_channels(
    q: str | None = Query(None, description="Поиск по базе"),
    category: str | None = Query(None, description="Фильтр category_id или all"),
    limit: int = Query(100, ge=1, le=500),
    offset: int = Query(0, ge=0),
):
    conn = await database.get_connection()
    try:
        rows, total = await database.list_channels(
            conn, q=q, category_id=category, limit=limit, offset=offset
        )
    finally:
        await conn.close()
    return {"total": total, "items": rows}


@app.patch("/api/channels/{row_id}")
async def patch_channel(row_id: int, body: ChannelCategoryPatch):
    if row_id < 1:
        raise HTTPException(status_code=400, detail="Некорректный id записи")
    cat_name = categorizer.category_display_name(body.category_id.strip())
    if cat_name is None:
        raise HTTPException(
            status_code=400,
            detail="Неизвестная категория. Список: GET /api/categories",
        )
    conn = await database.get_connection()
    try:
        updated = await database.update_channel_category(
            conn,
            row_id,
            category_id=body.category_id.strip(),
            category_name=cat_name,
        )
    finally:
        await conn.close()
    if not updated:
        raise HTTPException(status_code=404, detail="Запись не найдена")
    return {
        "ok": True,
        "id": row_id,
        "category_id": body.category_id.strip(),
        "category_name": cat_name,
    }


@app.delete("/api/channels/{row_id}")
async def delete_channel(row_id: int):
    if row_id < 1:
        raise HTTPException(status_code=400, detail="Некорректный id записи")
    conn = await database.get_connection()
    try:
        deleted = await database.delete_channel_by_id(conn, row_id)
    finally:
        await conn.close()
    if not deleted:
        raise HTTPException(status_code=404, detail="Запись не найдена")
    return {"ok": True, "id": row_id}


@app.get("/api/stats")
async def stats():
    conn = await database.get_connection()
    try:
        by_cat = await database.stats_by_category(conn)
        cur = await conn.execute("SELECT COUNT(*) FROM channels")
        r = await cur.fetchone()
        total = int(r[0]) if r else 0
    finally:
        await conn.close()
    return {"total_channels": total, "by_category": by_cat}


def _export_stamp() -> str:
    return datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")


@app.get("/api/export/csv")
async def export_csv(
    q: str | None = Query(None),
    category: str | None = Query(None),
):
    conn = await database.get_connection()
    try:
        rows = await database.list_channels_filtered(conn, q=q, category_id=category)
    finally:
        await conn.close()
    body = export_io.build_csv_bytes(rows)
    name = f"roadparser_{_export_stamp()}.csv"
    return Response(
        content=body,
        media_type="text/csv; charset=utf-8",
        headers={
            "Content-Disposition": f'attachment; filename="{name}"',
        },
    )


@app.get("/api/export/xlsx")
async def export_xlsx(
    q: str | None = Query(None),
    category: str | None = Query(None),
):
    conn = await database.get_connection()
    try:
        rows = await database.list_channels_filtered(conn, q=q, category_id=category)
    finally:
        await conn.close()
    body = export_io.build_xlsx_bytes(rows)
    name = f"roadparser_{_export_stamp()}.xlsx"
    return Response(
        content=body,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={
            "Content-Disposition": f'attachment; filename="{name}"',
        },
    )
