# Telegram CRM MVP

Минимальный SaaS CRM для общения с клиентами из Telegram через веб-интерфейс.

Что уже есть:

- Telegram webhook на FastAPI + aiogram принимает входящие сообщения.
- Менеджер видит список чатов и историю сообщений в React/Vite.
- Менеджер отвечает из веба, backend отправляет сообщение пользователю через Telegram Bot API.
- PostgreSQL хранит `users`, `chats`, `messages`.
- WebSocket обновляет интерфейс в realtime.
- Локальный запуск через Docker Compose.

## Структура проекта

```text
.
├── .env.example
├── docker-compose.yml
├── README.md
├── backend
│   ├── Dockerfile
│   ├── requirements.txt
│   ├── main.py
│   └── app
│       ├── __init__.py
│       ├── config.py
│       ├── database.py
│       ├── models.py
│       ├── schemas.py
│       ├── telegram.py
│       └── websocket.py
└── frontend
    ├── Dockerfile
    ├── index.html
    ├── package.json
    ├── vite.config.js
    └── src
        ├── api.js
        ├── App.jsx
        ├── main.jsx
        └── styles.css
```

## Основные файлы

- `docker-compose.yml` поднимает `db`, `backend`, `frontend`.
- `backend/main.py` содержит FastAPI app, CORS, REST API, Telegram webhook и WebSocket endpoint.
- `backend/app/models.py` содержит модели SQLAlchemy: `User`, `Chat`, `Message`.
- `backend/app/telegram.py` содержит aiogram bot setup, webhook setup и сохранение входящих сообщений.
- `backend/app/websocket.py` содержит простой in-memory WebSocket broadcaster.
- `frontend/src/App.jsx` содержит страницу CRM: список чатов, окно сообщений, поле отправки.

## API

- `GET /chats` — список чатов с последним сообщением.
- `GET /messages/{chat_id}` — сообщения выбранного CRM-чата.
- `POST /send-message` — отправка ответа в Telegram.
- `POST /telegram/webhook` — webhook для Telegram.
- `WS /ws` — realtime события для frontend.

## Быстрый локальный запуск

Проект может стартовать без Telegram токена, но реальные входящие/исходящие сообщения заработают после настройки BotFather и ngrok.

```bash
docker compose up
```

Открыть:

- Frontend: http://localhost:5173
- Backend: http://localhost:8000
- Swagger: http://localhost:8000/docs

## Настройка переменных окружения

Создайте локальный `.env`:

```bash
cp .env.example .env
```

Минимально важные переменные:

```env
TELEGRAM_BOT_TOKEN=123456:your_bot_token
PUBLIC_WEBHOOK_URL=https://your-ngrok-url.ngrok-free.app
TELEGRAM_WEBHOOK_SECRET=change_me_local_secret
```

## Как создать Telegram бота через BotFather

1. Откройте Telegram и найдите `@BotFather`.
2. Отправьте команду `/newbot`.
3. Укажите имя бота, например `My CRM Bot`.
4. Укажите username, который заканчивается на `bot`, например `my_crm_support_bot`.
5. BotFather вернет token вида `123456789:AA...`.
6. Вставьте token в `.env` как `TELEGRAM_BOT_TOKEN`.

## Как поднять ngrok

Установите и запустите ngrok:

```bash
ngrok http 8000
```

Скопируйте HTTPS URL, например:

```text
https://abc123.ngrok-free.app
```

Укажите его в `.env`:

```env
PUBLIC_WEBHOOK_URL=https://abc123.ngrok-free.app
```

Перезапустите backend:

```bash
docker compose up --build
```

Backend сам вызовет `setWebhook` при старте, если заданы `TELEGRAM_BOT_TOKEN` и `PUBLIC_WEBHOOK_URL`.

Webhook endpoint:

```text
https://abc123.ngrok-free.app/telegram/webhook
```

## Как проверить MVP

1. Запустите проект:

   ```bash
   docker compose up
   ```

2. Откройте frontend:

   ```text
   http://localhost:5173
   ```

3. Напишите сообщение вашему Telegram боту.
4. Чат появится в веб-интерфейсе.
5. Выберите чат, напишите ответ и нажмите `Отправить`.
6. Ответ уйдет пользователю в Telegram.

## Локальная разработка без Docker

Backend:

```bash
cd backend
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
uvicorn main:app --reload
```

Frontend:

```bash
cd frontend
npm install
npm run dev
```

PostgreSQL должен быть доступен по `DATABASE_URL`.

## Что можно развивать дальше

- Авторизация менеджеров.
- Миграции Alembic вместо `create_all`.
- Очередь фоновых задач для тяжелых Telegram операций.
- Несколько Telegram ботов на одного workspace.
- Роли, команды менеджеров и назначение чатов.
- Биллинг и ограничения тарифов.
