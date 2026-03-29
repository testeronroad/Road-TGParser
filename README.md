# RoadParcer

**Road Soft** · локальный каталог публичных **каналов и супергрупп Telegram**: поиск по ключевым словам, сохранение в **SQLite**, веб-интерфейс (поиск по базе, ручная смена категории, удаление записей), экспорт **CSV** и **Excel**. Стек: **Python 3.10+**, FastAPI, Telethon (MTProto).

## Быстрый старт

Полная пошаговая инструкция: **[INSTALL.md](INSTALL.md)**.

Кратко:

1. Установите **Python 3.10+**.
2. Создайте виртуальное окружение и выполните `pip install -r requirements.txt`.
3. Скопируйте `.env.example` в `.env`, укажите `API_ID` и `API_HASH` с [my.telegram.org/apps](https://my.telegram.org/apps).
4. Запустите `python login_telegram.py` (один раз, номер вводите в международном формате +(код страны)(номер), без пробелов).
5. Запустите сервер: `python -m uvicorn app.main:app --host 127.0.0.1 --port 8000`.
6. Откройте в браузере: `http://127.0.0.1:8000`.

Интерактивная документация API: `http://127.0.0.1:8000/docs`.

---

## Клонирование

```bash
git clone https://github.com/testeronroad/Road-TGParcer.git
cd Road-TGParcer
python -m venv .venv
# Windows PowerShell:
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

Дальше — по [INSTALL.md](INSTALL.md).

---

## Состав репозитория

| Путь | Назначение |
|------|------------|
| `app/` | Backend (FastAPI), веб-интерфейс в `app/static/` |
| `login_telegram.py` | Создание файла сессии Telegram |
| `requirements.txt` | Зависимости Python |
| `INSTALL.md` | Инструкция по запуску для пользователей |

Файлы `.env`, папка `data/` и сессии Telegram в репозиторий не входят (см. `.gitignore`).

---

## Лицензия

MIT, см. [LICENSE](LICENSE). Авторские права: **Testeron**.
