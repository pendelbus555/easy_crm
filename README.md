# Easy CRM — рабочее место менеджера для Telegram-диалогов

**Easy CRM** — MVP CRM для команд поддержки и продаж, которые общаются с клиентами через Telegram. Входящее сообщение из Telegram появляется в едином веб-интерфейсе, менеджер открывает историю диалога и отвечает клиенту, не переключаясь между чатами и Telegram-клиентом.

Проект демонстрирует интеграцию внешнего webhook API с асинхронным backend, хранение истории переписки и доставку обновлений в браузер в реальном времени.

> Статус: учебный/портфельный MVP. Авторизация менеджеров, роли и multi-tenant изоляция пока не входят в текущий scope.

## Пользовательский сценарий

```text
Клиент пишет Telegram-боту
          │
          ▼
Telegram webhook → FastAPI → PostgreSQL
          │                         │
          └──── WebSocket ──────────┘
                    │
                    ▼
        React-интерфейс менеджера
                    │
                    ▼
     Ответ менеджера → Telegram Bot API
```

1. Клиент отправляет сообщение боту.
2. Telegram вызывает защищённый webhook backend.
3. Backend создаёт или обновляет пользователя и чат, сохраняет сообщение.
4. WebSocket отправляет событие подключённым менеджерам — новый чат/сообщение появляется без перезагрузки.
5. Менеджер выбирает чат и отправляет ответ из CRM.
6. Backend отправляет текст через Telegram Bot API и сохраняет исходящее сообщение в истории.

## Возможности

- список диалогов, отсортированный по последней активности;
- карточка выбранного чата с историей входящих и исходящих сообщений;
- отправка ответа клиенту через Telegram Bot API;
- realtime-обновления списка чатов и текущего диалога через WebSocket;
- сохранение пользователей, чатов и сообщений в PostgreSQL;
- валидация webhook по `x-telegram-bot-api-secret-token`;
- автоматическая регистрация webhook при старте backend, если задан публичный URL;
- Swagger-документация FastAPI по адресу `/docs`;
- запуск всего окружения одной командой Docker Compose.

## Почему проект интересен технически

- **Интеграция с внешним сервисом:** Telegram Update преобразуется в доменные сущности CRM, а исходящие сообщения проходят обратный путь через Bot API.
- **Асинхронный стек:** FastAPI, `asyncio`, SQLAlchemy AsyncSession и `asyncpg` позволяют не блокировать обработку сетевых операций.
- **Realtime без polling:** WebSocket broadcaster доставляет событие `message_created` в браузер сразу после сохранения сообщения.
- **Целостная модель данных:** отдельные сущности `User`, `Chat` и `Message`, связи через foreign key, направления сообщений и временные метки.
- **Разделение frontend/backend:** React отвечает за состояние интерфейса, FastAPI — за API, интеграцию и persistence.

## Стек

| Слой | Технологии |
| --- | --- |
| Frontend | React, Vite, Axios, WebSocket API |
| Backend | Python, FastAPI, Uvicorn, Pydantic Settings |
| Telegram | aiogram, Bot API, webhook |
| Данные | PostgreSQL, SQLAlchemy 2, asyncpg |
| Инфраструктура | Docker, Docker Compose, ngrok для локального webhook |

## Структура проекта

```text
easy_crm/
├── docker-compose.yml          # db, backend и frontend
├── .env.example                # настройки локального окружения
├── backend/
│   ├── main.py                 # FastAPI app, REST API, webhook, WebSocket
│   ├── requirements.txt
│   └── app/
│       ├── config.py            # настройки через environment
│       ├── database.py          # async engine и session
│       ├── models.py            # User, Chat, Message
│       ├── schemas.py           # Pydantic-схемы API
│       ├── telegram.py          # bot, webhook и обработка Update
│       └── websocket.py         # менеджер realtime-подключений
└── frontend/
    ├── package.json
    ├── vite.config.js
    └── src/
        ├── App.jsx              # экран CRM и управление состоянием
        ├── api.js               # REST-клиент
        └── styles.css
```

## API

| Метод | Endpoint | Назначение |
| --- | --- | --- |
| `GET` | `/health` | health check backend |
| `GET` | `/chats` | список чатов с последним сообщением |
| `GET` | `/messages/{chat_id}` | история выбранного чата |
| `POST` | `/send-message` | отправить ответ в Telegram и сохранить его |
| `POST` | `/telegram/webhook` | принять Telegram Update |
| `WS` | `/ws` | события новых сообщений для frontend |

Swagger UI: <http://localhost:8000/docs>.

## Быстрый запуск через Docker

### 1. Подготовить окружение

```bash
cp .env.example .env
```

Для запуска интерфейса без реального Telegram-трафика достаточно оставить токен незаполненным. Для полноценного сценария получите токен у `@BotFather` и укажите его в `.env`:

```env
TELEGRAM_BOT_TOKEN=123456789:AA...
```

### 2. Запустить сервисы

```bash
docker compose up --build
```

Открыть:

- CRM: <http://localhost:5173>;
- backend: <http://localhost:8000>;
- Swagger: <http://localhost:8000/docs>.

PostgreSQL инициализируется автоматически при старте backend через `create_all`. Для остановки сервисов:

```bash
docker compose down
```

Чтобы удалить также volume с данными PostgreSQL, используйте `docker compose down -v`.

## Подключение Telegram webhook

Telegram требует публичный HTTPS-адрес. Для локальной демонстрации:

```bash
ngrok http 8000
```

Скопируйте HTTPS-адрес ngrok в `.env`:

```env
PUBLIC_WEBHOOK_URL=https://your-subdomain.ngrok-free.app
TELEGRAM_WEBHOOK_SECRET=change_me_local_secret
```

Backend сам зарегистрирует endpoint:

```text
https://your-subdomain.ngrok-free.app/telegram/webhook
```

Перезапустите окружение после изменения `.env`:

```bash
docker compose up --build
```

### Проверка полного сценария

1. Откройте CRM на `http://localhost:5173`.
2. Напишите вашему боту в Telegram.
3. Убедитесь, что новый чат появился в списке без перезагрузки страницы.
4. Откройте чат и отправьте ответ из CRM.
5. Проверьте доставку ответа в Telegram и появление исходящего сообщения в истории.

## Переменные окружения

| Переменная | Назначение |
| --- | --- |
| `DATABASE_URL` | async-подключение backend к PostgreSQL |
| `POSTGRES_DB`, `POSTGRES_USER`, `POSTGRES_PASSWORD` | параметры контейнера PostgreSQL |
| `FRONTEND_ORIGIN` | origin, разрешённый CORS |
| `VITE_API_URL` | базовый URL REST API для frontend |
| `VITE_WS_URL` | URL WebSocket для frontend |
| `TELEGRAM_BOT_TOKEN` | токен бота от BotFather |
| `PUBLIC_WEBHOOK_URL` | публичный HTTPS URL без `/telegram/webhook` |
| `TELEGRAM_WEBHOOK_SECRET` | секрет проверки входящего webhook |

## Локальная разработка без Docker

### Backend

```bash
cd backend
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
uvicorn main:app --reload
```

### Frontend

```bash
cd frontend
npm install
npm run dev
```

Для backend должен быть доступен PostgreSQL по `DATABASE_URL`, а frontend должен видеть backend по `VITE_API_URL` и `VITE_WS_URL`.

## Ограничения MVP и направления развития

- добавить авторизацию менеджеров, роли и разграничение доступа к чатам;
- заменить `create_all` на миграции Alembic;
- вынести realtime-доставку в Redis Pub/Sub или брокер сообщений для горизонтального масштабирования;
- добавить обработку медиа, файлов и других типов Telegram Update;
- добавить поиск, теги, статусы диалогов, назначение ответственного и непрочитанные сообщения;
- покрыть backend unit/integration-тестами и добавить frontend-тесты;
- настроить retry/idempotency для надёжной доставки webhook и исходящих сообщений.
