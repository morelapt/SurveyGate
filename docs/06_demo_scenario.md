# SurveyGate — Demo Scenario

Документ описывает минимальный локальный сценарий для демонстрации SurveyGate на собеседовании.

Цель demo — показать основной backend-flow:

```text
register user
-> update profile
-> create survey
-> create segment
-> preview segment
-> send invitations
-> create delivery job
-> open public invite
-> submit response
-> try to submit the same token again
```

---

## Что показывает demo

Этот сценарий демонстрирует:

- FastAPI endpoints;
- регистрацию пользователя через bot-like API;
- обновление профиля респондента;
- JSON-based segmentation;
- компиляцию сегмента в SQLAlchemy-запрос;
- operator API с защитой через `X-API-Key`;
- генерацию одноразового invitation token;
- хранение только `token_hash`;
- создание `Invitation`;
- создание `InvitationDeliveryJob`;
- Redis/RQ-ready delivery architecture;
- public invite open/submit flow;
- защиту от повторного submit по тому же token.

---

## Prerequisites

Начать лучше с чистой локальной базы.

```bash
cp .env.example .env
docker compose up -d
poetry install
poetry run python -m alembic upgrade head
poetry run python -m uvicorn app.main:app --reload
```

API будет доступен по адресу:

```text
http://127.0.0.1:8000
```

Swagger UI:

```text
http://127.0.0.1:8000/docs
```

Operator endpoints требуют API key:

```text
X-API-Key: dev-operator-key
```

---

## Optional: запуск worker

Для полного показа delivery flow можно открыть второй терминал и запустить worker:

```bash
poetry run rq worker invitation_delivery
```

Если worker не запускать, demo всё равно можно пройти через invite link, который возвращается в response от `send_invitations`.

Разница:

- без worker invitation останется в статусе `queued`;
- с worker delivery job будет обработан, а invitation перейдёт в `sent`.

---

## 1. Register user

Endpoint имитирует регистрацию пользователя через Telegram-бота.

```bash
curl -X POST "http://127.0.0.1:8000/bot/users/register" \
  -H "Content-Type: application/json" \
  -d '{
    "telegram_id": 100001
  }'
```

Expected response:

```json
{
  "is_new": true,
  "user_id": 1
}
```

Если пользователь уже существует, API вернёт:

```json
{
  "is_new": false,
  "user_id": 1
}
```

---

## 2. Update user profile

```bash
curl -X PATCH "http://127.0.0.1:8000/bot/users/profile" \
  -H "Content-Type: application/json" \
  -d '{
    "telegram_id": 100001,
    "city": "Moscow",
    "age": 25,
    "has_children": false,
    "devices": [],
    "services": []
  }'
```

Expected response:

```json
{
  "ok": true
}
```

---

## 3. Create survey

```bash
curl -X POST "http://127.0.0.1:8000/operator/surveys" \
  -H "X-API-Key: dev-operator-key" \
  -H "Content-Type: application/json" \
  -d '{
    "title": "UX Interview Study",
    "status": "active"
  }'
```

Expected response:

```json
{
  "survey_id": 1
}
```

---

## 4. Create segment

Сегмент выбирает пользователей из Moscow в возрасте от 18 до 35 лет.

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

Expected response:

```json
{
  "segment_id": 1
}
```

---

## 5. Preview segment

```bash
curl -X GET "http://127.0.0.1:8000/operator/segments/1/preview?limit=20" \
  -H "X-API-Key: dev-operator-key"
```

Expected response:

```json
{
  "segment_id": 1,
  "user_ids": [1]
}
```

Если база не пустая, IDs могут отличаться. Главное — в ответе должны быть пользователи, подходящие под JSON-сегмент.

---

## 6. Send invitations

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

Expected response:

```json
{
  "send_id": 1,
  "targeted": 1,
  "created": 1,
  "resent": 0,
  "skipped": 0,
  "created_invites": [
    {
      "user_id": 1,
      "invitation_id": 1,
      "invite_link": "/s/1/<token>"
    }
  ]
}
```

Важно:

- raw token возвращается только для локального demo;
- в базе хранится только `token_hash`;
- создаётся `Invitation`;
- создаётся `InvitationDeliveryJob`;
- delivery job ставится в Redis/RQ queue.

В production bulk API не должен свободно возвращать raw invite links, потому что такая ссылка является bearer-secret.

---

## 7. Open public invite

Возьми `invite_link` из предыдущего response.

Пример:

```bash
curl -X GET "http://127.0.0.1:8000/s/1/<token>"
```

Expected response без запущенного worker:

```json
{
  "survey_id": 1,
  "invitation_id": 1,
  "status": "queued"
}
```

Expected response после обработки worker-ом:

```json
{
  "survey_id": 1,
  "invitation_id": 1,
  "status": "opened"
}
```

Пояснение:

- `queued` означает, что invitation создан и delivery job поставлена в очередь;
- `opened` означает, что invitation был доставлен/помечен как `sent`, а потом пользователь открыл ссылку.

---

## 8. Submit response

```bash
curl -X POST "http://127.0.0.1:8000/s/1/<token>" \
  -H "Content-Type: application/json" \
  -d '{
    "answers": {
      "q1": "I use online cinemas weekly",
      "q2": 5
    }
  }'
```

Expected response:

```json
{
  "ok": true,
  "response_id": 1
}
```

После successful submit:

- response сохраняется в PostgreSQL;
- invitation получает `used_at`;
- invitation переходит в `completed`;
- тот же token больше нельзя использовать для повторного submit.

---

## 9. Try to submit the same token again

```bash
curl -X POST "http://127.0.0.1:8000/s/1/<token>" \
  -H "Content-Type: application/json" \
  -d '{
    "answers": {
      "q1": "Second attempt",
      "q2": 1
    }
  }'
```

Expected response:

```json
{
  "detail": "Invitation already used"
}
```

Это подтверждает, что public invite token одноразовый.

---

## Что сказать на собеседовании

Короткое объяснение demo:

> Я начинаю с пользователя, который регистрируется через bot-like API и заполняет профиль.  
> Затем создаю survey и reusable JSON-сегмент.  
> Segment валидируется и компилируется в SQLAlchemy-запрос.  
> При запуске рассылки система выбирает подходящих пользователей, создаёт invitations, генерирует одноразовые tokens, сохраняет только token hashes и создаёт delivery jobs.  
> Delivery jobs отправляются в Redis/RQ queue, а worker может обработать их отдельно от HTTP-запроса.  
> После этого пользователь открывает public invite link и отправляет response.  
> Повторный submit по тому же token блокируется.

---

## Главное, что демонстрирует проект

SurveyGate показывает не просто CRUD, а полноценный backend-flow:

```text
segmentation
-> invitation generation
-> secure token flow
-> async delivery architecture
-> public response submission
-> single-use token protection
```

Текущая доставка через Telegram пока заменена stub-логикой, но архитектура уже разделяет бизнес-сущность `Invitation` и техническую задачу `InvitationDeliveryJob`.