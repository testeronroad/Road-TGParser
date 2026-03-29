from __future__ import annotations

_RULES: list[tuple[str, str, tuple[str, ...]]] = [
    (
        "crypto",
        "Крипта",
        (
            "крипт",
            "bitcoin",
            "btc",
            "eth",
            "ethereum",
            "биткоин",
            "эфир",
            "токен",
            "defi",
            "nft",
            "бирж",
            "binance",
            "трейд",
            "альткоин",
            "mining",
            "майнинг",
        ),
    ),
    (
        "arbitrage",
        "Арбитраж",
        (
            "арбитраж",
            "арбитр",
            "вбив",
            "поставк",
            "dropship",
            "дропшип",
            "resell",
            "перепрод",
        ),
    ),
    (
        "scam",
        "Скам / мошенничество",
        (
            "скам",
            "развод",
            "лохотрон",
            "обман",
            "мошен",
            "пирамида",
            "хайп",
            "scam",
            "fraud",
        ),
    ),
    (
        "online_earn",
        "Заработок онлайн",
        (
            "заработ",
            "деньг онлайн",
            "удалённ",
            "удаленн",
            "фриланс",
            "инвест",
            "пассивн",
            "доход",
            "money online",
            "earn",
            "работа на дому",
        ),
    ),
    (
        "shop",
        "Онлайн-магазин",
        (
            "магазин",
            "shop",
            "store",
            "доставк",
            "заказ",
            "опт",
            "розниц",
            "товар",
            "sale",
        ),
    ),
    (
        "news",
        "Новости / медиа",
        (
            "новост",
            "news",
            "медиа",
            "журнал",
            "газет",
            "репорт",
            "breaking",
        ),
    ),
    (
        "tech",
        "IT / технологии",
        (
            "it ",
            " it",
            "програм",
            "код",
            "dev",
            "developer",
            "python",
            "linux",
            "сервер",
            "api",
            "стартап",
            "tech",
        ),
    ),
    (
        "betting",
        "Ставки / казино",
        (
            "ставк",
            "казино",
            "slot",
            "букмек",
            "bet ",
            "betting",
            "poker",
            "слот",
        ),
    ),
    (
        "education",
        "Обучение",
        (
            "курс",
            "обучен",
            "урок",
            "школ",
            "тренинг",
            "webinar",
            "вебинар",
            "education",
        ),
    ),
    (
        "marketing",
        "Маркетинг / реклама",
        (
            "маркетинг",
            "реклам",
            "smm",
            "таргет",
            "seo",
            "продвижен",
            "лидоген",
        ),
    ),
]


def classify(title: str, description: str) -> tuple[str, str]:
    text = f"{title or ''} {description or ''}".lower()
    for cat_id, display, keywords in _RULES:
        for kw in keywords:
            if kw.lower() in text:
                return cat_id, display
    return "other", "Другое"


def all_categories() -> list[dict[str, str]]:
    return [{"id": r[0], "name": r[1]} for r in _RULES] + [
        {"id": "other", "name": "Другое"}
    ]


def category_display_name(category_id: str) -> str | None:
    for c in all_categories():
        if c["id"] == category_id:
            return c["name"]
    return None
