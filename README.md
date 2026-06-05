# SurveyGate — Backend MVP платформы для UX-рекрутинга

SurveyGate — это backend MVP сервиса для рекрутинга UX-респондентов и управления приглашениями на опросы.

Проект демонстрирует асинхронный backend на FastAPI с хранением профилей пользователей, JSON-сегментацией аудитории, генерацией безопасных invitation links, публичным flow открытия/отправки ответа и асинхронной обработкой доставки через Redis/RQ worker.

## TL;DR

SurveyGate решает задачу targeted-рекрутинга респондентов для UX-исследований.

Основной flow:

1. Респондент регистрируется через bot-like Telegram identity flow.
2. Оператор создаёт опрос и JSON-сегмент аудитории.
3. Система валидирует сегмент, компилирует его в SQLAlchemy-запрос и находит подходящих пользователей.
4. Для подходящих пользователей создаются уникальные одноразовые invitation links.
5. Delivery jobs сохраняются в PostgreSQL и ставятся в Redis/RQ очередь.
6. Отдельный RQ worker обрабатывает задачи доставки.
7. Респондент открывает публичную tokenized-ссылку и отправляет ответ на опрос.

Проект сфокусирован на backend-архитектуре: async FastAPI, SQLAlchemy 2.0, PostgreSQL, Alembic migrations, Redis/RQ, secure token handling, background jobs и разделение бизнес-логики по service layer.

## Проблема

UX-исследователям часто нужно:

- находить подходящих респондентов;
- фильтровать пользователей по профилю;
- отправлять приглашения на опросы или интервью;
- не контактировать повторно с одним и тем же респондентом без необходимости;
- отслеживать, было ли приглашение отправлено, открыто и завершено.

Во многих командах этот процесс собирается вручную из Google Forms, таблиц, Telegram-чатов и ручной рассылки. Такой workflow плохо масштабируется, сложно аудируется и легко ломается при росте количества респондентов.

## MVP Scope

Проект реализует backend-слой рекрутинговой платформы.

В текущем MVP реализовано:

- регистрация и обновление профиля пользователя через bot-like API;
- operator API, защищённый через `X-API-Key`;
- создание опросов;
- создание JSON-сегментов;
- preview пользователей, подходящих под сегмент;
- генерация приглашений;
- хранение только hash от invitation token;
- публичный flow открытия invitation link и отправки ответа;
- создание delivery jobs;
- интеграция с Redis/RQ для постановки задач доставки в очередь;
- отдельный RQ worker для обработки delivery jobs;
- PostgreSQL schema migrations через Alembic;
- автоматические тесты для core flows.

Текущие ограничения MVP:

- нет UI/admin panel;
- нет production-grade authentication/authorization;
- operator API пока защищён упрощённо через `X-API-Key`;
- реальная интеграция с Telegram Bot API ещё не подключена;
- отправка сообщений сейчас представлена stub sender’ом;
- нет rate limiting;
- нет полноценного observability stack;
- нет production deployment configuration;
- нет полноценной retry/backoff/dead-letter логики для failed delivery jobs.

## Почему это не просто CRUD

SurveyGate содержит не только операции создания/чтения/обновления сущностей, а полноценный доменный backend workflow:

- JSON-сегменты валидируются и компилируются в SQLAlchemy-запросы;
- система находит пользователей, подходящих под audience segment;
- для каждого пользователя создаётся уникальный tokenized invitation link;
- raw tokens не хранятся в базе, вместо них сохраняется только hash;
- `Invitation` отделён от `InvitationDeliveryJob`, чтобы не смешивать бизнес-доступ к опросу и техническую доставку сообщения;
- delivery вынесен из HTTP request/response cycle в Redis/RQ worker;
- публичный invite flow отслеживает state transitions: `sent -> opened -> completed`;
- resend/revocation logic позволяет заменить активное приглашение новым без хранения старого raw token.

## Архитектура

```text
Operator / Bot-like client / Respondent
              |
              v
        FastAPI application
              |
              +--------------------+
              |                    |
              v                    v
        PostgreSQL             Redis / RQ
        source of truth        delivery queue
              ^                    |
              |                    v
              +------------ RQ Worker
                            |
                            v
                    Stub sender / future Telegram API
```

PostgreSQL хранит бизнес-состояние системы:

- users;
- user identities;
- surveys;
- segments;
- survey sends;
- invitations;
- invitation delivery jobs;
- responses.

Redis/RQ используется как transport layer для фоновых задач доставки.

Worker — отдельный процесс. Он слушает очередь `invitation_delivery`, загружает `InvitationDeliveryJob` из PostgreSQL, обрабатывает доставку и обновляет статус задачи в базе.

## Tech Stack

- Python 3.12
- FastAPI
- Pydantic
- SQLAlchemy 2.0 async
- PostgreSQL
- Alembic
- Redis
- RQ
- Docker Compose
- pytest
- pytest-asyncio
- ruff

## Основные доменные сущности

### User

Респондент, которого можно пригласить к участию в опросе.

### UserIdentity

Внешняя идентичность пользователя, например Telegram identity.

Вынос identity в отдельную сущность позволяет не смешивать бизнес-профиль пользователя и внешний канал регистрации/доставки.

### Segment

Переиспользуемый JSON-фильтр, описывающий аудиторию, которую нужно таргетировать.

Пример:

```json
{
  "op": "AND",
  "rules": [
    {"field": "city", "op": "EQ", "value": "Moscow"},
    {"field": "age", "op": "BETWEEN", "value": [18, 35]}
  ]
}
```

Сегмент сначала валидируется, а затем компилируется в SQLAlchemy query.

### Survey

Опрос или исследовательская активность, на которую можно приглашать пользователей.

### SurveySend

Конкретный запуск рассылки приглашений по опросу и сегменту.

### Invitation

Бизнес-сущность, которая представляет право конкретного пользователя открыть публичную ссылку и отправить ответ на опрос.

Raw token показывается только при создании invite link. В базе хранится только hash токена.

### InvitationDeliveryJob

Техническая сущность доставки приглашения.

Разделение сделано намеренно:

- `Invitation` отвечает на вопрос: “Может ли этот пользователь получить доступ к этому опросу?”
- `InvitationDeliveryJob` отвечает на вопрос: “Была ли технически обработана доставка сообщения?”

## State Flows

### Survey

```text
draft -> active -> closed
```

### Invitation

```text
queued -> sent -> opened -> completed
            |
            +-> revoked
            +-> expired
```

### InvitationDeliveryJob

```text
pending -> queued -> processing -> sent
                                |
                                +-> failed
```

## API Overview

### Health

```http
GET /health
GET /health/db
```

### Bot-like User API

```http
POST /bot/users/register
GET /bot/users/profile
PATCH /bot/users/profile
```

### Operator API

Все operator endpoints требуют header:

```http
X-API-Key: <operator-api-key>
```

Доступные endpoints:

```http
GET /operator/ping
POST /operator/surveys
POST /operator/segments
GET /operator/segments/{segment_id}/preview
POST /operator/surveys/{survey_id}/send_invitations
```

### Public Invite API

```http
GET /s/{survey_id}/{token}
POST /s/{survey_id}/{token}
```

## Quick Start

Этот quick start запускает PostgreSQL и Redis через Docker Compose, а FastAPI app и RQ worker запускаются локально через Poetry.

Production Dockerfile и отдельные полностью dockerized API/worker containers указаны в roadmap как следующий шаг production readiness.

### 1. Склонировать репозиторий

```bash
git clone https://github.com/morelapt/SurveyGate.git
cd SurveyGate
git checkout feature/redis-delivery-queue
```

### 2. Создать локальный `.env`

```bash
cp .env.example .env
```

Пример локальных значений:

```env
ENV=dev

POSTGRES_DB=surveygate
POSTGRES_USER=surveygate
POSTGRES_PASSWORD=surveygate
DATABASE_HOST=localhost
DATABASE_PORT=5432

DATABASE_URL=postgresql+asyncpg://surveygate:surveygate@localhost:5432/surveygate
DATABASE_URL_SYNC=postgresql+psycopg://surveygate:surveygate@localhost:5432/surveygate

REDIS_URL=redis://localhost:6379/0

OPERATOR_API_KEY=dev-operator-key
SECRET_KEY=dev-secret-key-change-me
```

Настоящий `.env` не должен попадать в GitHub. В репозитории должен храниться только `.env.example` без production-секретов.

### 3. Запустить инфраструктуру

```bash
docker compose up -d
```

В текущем local setup Docker Compose поднимает инфраструктурные сервисы: PostgreSQL и Redis.

### 4. Установить зависимости

```bash
poetry install
```

### 5. Применить миграции

```bash
poetry run python -m alembic upgrade head
```

### 6. Заполнить справочники

```bash
poetry run python -m app.scripts.seed_catalogs
```

### 7. Запустить API

```bash
poetry run python -m uvicorn app.main:app --reload
```

### 8. Запустить RQ worker

В отдельном терминале:

```bash
PYTHONPATH=. poetry run rq worker invitation_delivery --url redis://localhost:6379/0
```

Worker слушает очередь `invitation_delivery`, загружает delivery jobs из PostgreSQL и обновляет их статус после обработки.

### 9. Открыть API docs

```text
http://127.0.0.1:8000/docs
```

## Tests and Linting

Запуск тестов:

```bash
poetry run python -m pytest
```

Запуск linting:

```bash
poetry run ruff check .
```

Проверка форматирования:

```bash
poetry run ruff format --check .
```

## Example Flow

Ниже — минимальный demo-flow для ручной проверки основного сценария.

### 1. Create a survey

```bash
curl -X POST "http://127.0.0.1:8000/operator/surveys" \
  -H "X-API-Key: dev-operator-key" \
  -H "Content-Type: application/json" \
  -d '{
    "title": "UX Interview Study",
    "status": "draft"
  }'
```

### 2. Create a segment

```bash
curl -X POST "http://127.0.0.1:8000/operator/segments" \
  -H "X-API-Key: dev-operator-key" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "Moscow users 18-35",
    "filters": {
      "op": "AND",
      "rules": [
        {"field": "city", "op": "EQ", "value": "Moscow"},
        {"field": "age", "op": "BETWEEN", "value": [18, 35]}
      ]
    }
  }'
```

### 3. Preview segment users

```bash
curl -X GET "http://127.0.0.1:8000/operator/segments/1/preview?limit=20" \
  -H "X-API-Key: dev-operator-key"
```

### 4. Send invitations

```bash
curl -X POST "http://127.0.0.1:8000/operator/surveys/1/send_invitations" \
  -H "X-API-Key: dev-operator-key" \
  -H "Content-Type: application/json" \
  -d '{
    "segment_id": 1,
    "message_template": "Please take part in our research: {link}",
    "ttl_days": 14,
    "limit": 100
  }'
```

В локальном demo response может содержать сгенерированные invite links.

В production-системе invitation links являются bearer secrets и не должны свободно возвращаться из bulk API response.

### 5. Open public invite link

Подставьте `survey_id` и `token` из созданной invite link:

```bash
curl -X GET "http://127.0.0.1:8000/s/1/<token>"
```

Открытие ссылки переводит invitation в состояние `opened`, если invitation валиден, не истёк, не отозван и ещё не завершён.

### 6. Submit response

```bash
curl -X POST "http://127.0.0.1:8000/s/1/<token>" \
  -H "Content-Type: application/json" \
  -d '{
    "answers": {
      "q1": "yes",
      "q2": "I use this service weekly"
    }
  }'
```

После успешной отправки создаётся `Response`, а invitation переходит в состояние `completed`.

## Demo Scenario

Более подробный пошаговый demo-flow доступен в:

```text
docs/06_demo_scenario.md
```

## Project Structure

```text
surveygate/
├── app/
│   ├── core/
│   ├── db/
│   ├── models/
│   ├── queue/
│   ├── routers/
│   ├── schemas/
│   ├── scripts/
│   ├── services/
│   └── main.py
├── docs/
├── migrations/
├── tests/
├── docker-compose.yml
├── pyproject.toml
└── README.md
```

## Key Design Decisions

### JSON-based segmentation

Сегменты хранятся как JSON trees.

Почему это полезно для MVP:

- быстро реализовать;
- достаточно гибко для разных фильтров;
- можно валидировать до выполнения запроса;
- можно компилировать в SQLAlchemy queries;
- операторская логика сегментации не требует ручного SQL.

Trade-offs:

- сложнее оптимизировать, чем полностью нормализованные rule tables;
- нужна строгая validation layer;
- сложнее делать аналитику по структуре сегментов;
- нужно явно ограничивать доступные поля и операторы, чтобы не превратить DSL в небезопасный query builder.

### Hashed invitation tokens

Raw invitation tokens не хранятся в базе.

Flow:

1. генерируется криптографически случайный token;
2. token показывается только в public invite link;
3. в PostgreSQL сохраняется только hash токена;
4. при public request входящий token снова хэшируется и сравнивается с сохранённым hash.

Это снижает ущерб при потенциальной утечке базы: attacker не сможет напрямую использовать raw invitation links только по данным из таблицы.

### Invitation vs InvitationDeliveryJob

Проект разделяет business state и delivery mechanics.

`Invitation` — бизнес-объект:

- кому выдан доступ;
- к какому survey;
- активен ли invitation;
- истёк ли он;
- был ли открыт;
- был ли завершён;
- был ли отозван.

`InvitationDeliveryJob` — техническая задача доставки:

- какой invitation нужно доставить;
- какой текст отправить;
- в каком статусе находится доставка;
- сколько было attempts;
- какая была последняя ошибка;
- когда задача была поставлена в очередь;
- когда сообщение было отправлено.

Это разделение позволяет развивать retries, backoff, failed jobs, worker recovery и Telegram integration без смешивания технической доставки с бизнес-моделью доступа к опросу.

### Redis/RQ queue

Redis/RQ используется, чтобы вынести доставку приглашений из HTTP request/response cycle.

Текущая MVP-реализация:

- delivery jobs хранятся в PostgreSQL;
- jobs ставятся в Redis/RQ очередь;
- отдельный worker обрабатывает queue;
- фактическая отправка через Telegram пока заменена stub sender’ом.

Для production PostgreSQL должен оставаться source of truth, а Redis/RQ — transport layer для фоновой обработки.

## Production Readiness

SurveyGate намеренно является backend MVP, а не production-ready коммерческим продуктом.

Перед реальным запуском важнее всего закрыть следующие gaps.

### Security and Access Control

- production-grade authentication and authorization;
- RBAC для операторов;
- защита bot-facing endpoints;
- audit log для действий операторов;
- rate limiting;
- HTTPS и reverse proxy configuration;
- production-grade secrets management.

### Delivery Reliability

- реальная интеграция с Telegram Bot API;
- retry/backoff policy для failed delivery jobs;
- dead-letter logic;
- outbox или sweeper process для queue reliability;
- recovery stale `processing` jobs;
- worker heartbeat;
- idempotency keys для bulk sends.

### Data and Privacy

- аккуратная обработка персональных данных;
- user deletion flow;
- retention policy;
- auditability для изменений данных;
- validation of survey answers against a survey schema.

### Operations and Deployment

- production Dockerfile;
- отдельные API/worker containers;
- readiness/liveness checks;
- metrics and alerts для queue health;
- structured logging;
- CI pipeline для linting, tests и migration checks;
- deployment configuration для staging/production.

Подробнее production gaps описаны в:

```text
docs/05_production_readiness.md
```

## Interview Positioning

Этот проект лучше презентовать как:

> Backend MVP для targeted UX research recruitment.
> Проект демонстрирует async FastAPI development, SQLAlchemy 2.0,
> PostgreSQL schema design, JSON-based segmentation, secure invitation tokens,
> public invite flow и Redis/RQ-based delivery queue.
> Проект не является production-ready, но основные production gaps описаны и архитектурно понятны.

Короткая устная версия:

> SurveyGate — это backend MVP сервиса для рекрутинга UX-респондентов и управления приглашениями на опросы. Оператор создаёт survey и JSON-сегмент, система находит подходящих пользователей, создаёт для них безопасные invitation links и ставит delivery jobs в Redis/RQ очередь. Доставка обрабатывается отдельным worker’ом, а PostgreSQL хранит бизнес-состояние. Из важных решений: raw tokens не хранятся в базе, `Invitation` отделён от `InvitationDeliveryJob`, а сегменты задаются через JSON DSL вместо raw SQL.

## Interview Notes

Личные заметки для подготовки к интервью доступны в:

```text
docs/07_interview_notes.md
```

## Author

Marat Magomedov