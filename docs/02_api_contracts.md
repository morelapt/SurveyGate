# SurveyGate — API Contracts

Документ описывает актуальные API-контракты SurveyGate MVP.

Фокус документа — входные/выходные payloads, назначение endpoints и основные ошибки.  
Реализация, внутренняя бизнес-логика и детали БД здесь не описываются.

---

## Common

### Base API

Локально API доступен через FastAPI-приложение.

Swagger UI:

```text
/docs
```

---

### Health

#### GET /health

Проверка, что приложение запущено.

Response:

```json
{
  "status": "ok"
}
```

---

#### GET /health/db

Проверка соединения с базой данных.

Response:

```json
{
  "db": 1
}
```

---

## Bot-side API

Bot-side endpoints имитируют API, которым в будущем будет пользоваться Telegram-бот.

---

### POST /bot/users/register

Создать пользователя по `telegram_id`.

Если пользователь с таким `telegram_id` уже существует, endpoint возвращает существующего пользователя и `is_new = false`.

Request:

```json
{
  "telegram_id": 123456
}
```

Validation:

- `telegram_id` должен быть integer;
- `telegram_id >= 1`.

Response:

```json
{
  "is_new": true,
  "user_id": 1
}
```

Response fields:

| Field | Type | Description |
|---|---:|---|
| `is_new` | boolean | Был ли создан новый пользователь |
| `user_id` | integer | ID пользователя |

Notes:

- В текущем MVP `user_id` — integer, не UUID.
- Поля `language` и `source` сейчас не входят в контракт.

---

### PATCH /bot/users/profile

Обновить анкету пользователя.

Request:

```json
{
  "telegram_id": 123456,
  "age": 33,
  "city": "Москва",
  "has_children": false,
  "devices": ["tv"],
  "services": ["ivi"]
}
```

Request fields:

| Field | Type | Required | Description |
|---|---:|---:|---|
| `telegram_id` | integer | yes | Telegram ID пользователя |
| `age` | integer/null | no | Возраст, от 0 до 120 |
| `city` | string/null | no | Город пользователя |
| `has_children` | boolean/null | no | Есть ли дети |
| `devices` | array[string] | no | Список device codes |
| `services` | array[string] | no | Список service codes |

Validation:

- `telegram_id >= 1`;
- `age` должен быть от `0` до `120`;
- `devices` должны содержать существующие device codes;
- `services` должны содержать существующие service codes.

Response:

```json
{
  "ok": true
}
```

Errors:

| Status | Meaning |
|---:|---|
| `400` | Неизвестный device/service code |
| `404` | Пользователь не зарегистрирован |
| `422` | Некорректный request payload |

---

### Not implemented: POST /bot/users/delete_me

В текущем MVP endpoint `/bot/users/delete_me` не реализован.

Его не стоит описывать как актуальный контракт.

Можно оставить как future API:

```text
POST /bot/users/delete_me
```

Планируемый смысл:

- soft-delete пользователя;
- удалить/обезличить identity;
- отозвать активные invitations;
- сохранить агрегированную статистику.

---

## Operator-side API

Operator-side endpoints предназначены для оператора/исследователя.

Все operator endpoints требуют заголовок:

```http
X-API-Key: <operator-api-key>
```

Если ключ отсутствует или неверный, API возвращает:

```text
401 Unauthorized
```

---

### GET /operator/ping

Проверка operator API и API-key.

Headers:

```http
X-API-Key: dev-operator-key
```

Response:

```json
{
  "ok": true
}
```

Errors:

| Status | Meaning |
|---:|---|
| `401` | Invalid or missing X-API-Key |

---

### POST /operator/surveys

Создать survey.

Headers:

```http
X-API-Key: dev-operator-key
```

Request:

```json
{
  "title": "UX Interview Study",
  "status": "draft"
}
```

Request fields:

| Field | Type | Required | Description |
|---|---:|---:|---|
| `title` | string | yes | Название survey |
| `status` | string | no | Статус survey, по умолчанию `draft` |

Response:

```json
{
  "survey_id": 1
}
```

Response fields:

| Field | Type | Description |
|---|---:|---|
| `survey_id` | integer | ID созданного survey |

Errors:

| Status | Meaning |
|---:|---|
| `401` | Invalid or missing X-API-Key |
| `422` | Некорректный request payload |

Notes:

- В текущем MVP `survey_id` — integer, не UUID.
- Типовые статусы survey: `draft`, `active`, `closed`.

---

### POST /operator/segments

Создать сегмент пользователей.

Headers:

```http
X-API-Key: dev-operator-key
```

Request:

```json
{
  "name": "Moscow users 18-35",
  "filters": {
    "op": "AND",
    "rules": [
      {
        "field": "city",
        "op": "EQ",
        "value": "Moscow"
      },
      {
        "field": "age",
        "op": "BETWEEN",
        "value": [18, 35]
      }
    ]
  }
}
```

Request fields:

| Field | Type | Required | Description |
|---|---:|---:|---|
| `name` | string | yes | Название сегмента |
| `filters` | object | yes | JSON DSL фильтров |

Response:

```json
{
  "segment_id": 1
}
```

Errors:

| Status | Meaning |
|---:|---|
| `401` | Invalid or missing X-API-Key |
| `422` | Некорректный request payload или invalid segment filters |

---

### GET /operator/segments/{segment_id}/preview

Предпросмотр пользователей, подходящих под сегмент.

Headers:

```http
X-API-Key: dev-operator-key
```

Path params:

| Param | Type | Description |
|---|---:|---|
| `segment_id` | integer | ID сегмента |

Query params:

| Param | Type | Default | Description |
|---|---:|---:|---|
| `limit` | integer | `20` | Максимальное число user IDs в ответе |

Example:

```text
GET /operator/segments/1/preview?limit=20
```

Response:

```json
{
  "segment_id": 1,
  "user_ids": [1, 2, 3]
}
```

Errors:

| Status | Meaning |
|---:|---|
| `401` | Invalid or missing X-API-Key |
| `404` | Segment not found |
| `422` | Некорректные path/query параметры |

Notes:

- В текущем MVP preview endpoint использует `GET`, не `POST`.
- Endpoint возвращает только список `user_ids`, а не полные профили пользователей.

---

### POST /operator/surveys/{survey_id}/send_invitations

Запустить рассылку survey по segment.

Endpoint:

```text
POST /operator/surveys/{survey_id}/send_invitations
```

Headers:

```http
X-API-Key: dev-operator-key
```

Path params:

| Param | Type | Description |
|---|---:|---|
| `survey_id` | integer | ID survey |

Request:

```json
{
  "segment_id": 1,
  "message_template": "Please take part in our research: {link}",
  "ttl_days": 14,
  "limit": 100
}
```

Request fields:

| Field | Type | Required | Description |
|---|---:|---:|---|
| `segment_id` | integer | yes | ID сегмента |
| `message_template` | string | yes | Шаблон сообщения |
| `ttl_days` | integer | no | TTL invitation в днях, default `14` |
| `limit` | integer | no | Максимум пользователей, default `200` |

Validation:

- `message_template` не должен быть пустым;
- `ttl_days` от `1` до `365`;
- `limit` от `1` до `5000`.

Response:

```json
{
  "send_id": 1,
  "targeted": 400,
  "created": 350,
  "resent": 50,
  "skipped": 0,
  "created_invites": [
    {
      "user_id": 1,
      "invitation_id": 10,
      "invite_link": "/s/1/raw-token-example"
    }
  ]
}
```

Response fields:

| Field | Type | Description |
|---|---:|---|
| `send_id` | integer | ID созданного SurveySend |
| `targeted` | integer | Сколько пользователей попало в segment query |
| `created` | integer | Сколько новых invitations создано |
| `resent` | integer | Сколько активных старых invitations было отозвано и заменено |
| `skipped` | integer | Сколько пользователей было пропущено |
| `created_invites` | array | Созданные invitations и demo invite links |

`created_invites[]` item:

| Field | Type | Description |
|---|---:|---|
| `user_id` | integer | ID пользователя |
| `invitation_id` | integer | ID invitation |
| `invite_link` | string | Public invite link |

Errors:

| Status | Meaning |
|---:|---|
| `400` | Survey is closed |
| `401` | Invalid or missing X-API-Key |
| `404` | Survey or segment not found |
| `422` | Некорректный request payload |

Notes:

- В текущем MVP response fields называются `targeted`, `created`, `resent`, `skipped`, а не `users_targeted`, `invitations_created`, `invitations_resend`.
- В текущем MVP `send_id` — integer, не UUID.
- `created_invites.invite_link` возвращается для demo/local flow.
- В production bulk API не должен свободно возвращать raw invite tokens, потому что invite link является bearer-secret.

---

### Not implemented: GET /operator/surveys/{survey_id}/stats

В текущем MVP endpoint статистики survey не реализован.

Его не стоит описывать как актуальный контракт.

Можно оставить как future API:

```text
GET /operator/surveys/{survey_id}/stats
```

Потенциальные метрики:

```json
{
  "invited": 400,
  "sent": 380,
  "opened": 120,
  "completed": 60,
  "conversion_opened": 0.315,
  "conversion_completed": 0.158
}
```

Notes:

- `promo_issued` неактуален для текущего MVP, потому что promo codes сейчас не реализованы.

---

## Public Invite API

Public endpoints обслуживают открытие invite link и отправку ответа пользователем.

Important implementation note:

В коде есть router для public endpoints, но нужно убедиться, что он подключён в `app.main` через `app.include_router(public_router)`.  
Если router не подключён, endpoints `/s/{survey_id}/{token}` не будут доступны в запущенном FastAPI-приложении.

---

### GET /s/{survey_id}/{token}

Открыть public invite link.

Path params:

| Param | Type | Description |
|---|---:|---|
| `survey_id` | integer | ID survey |
| `token` | string | Raw invitation token из ссылки |

Response:

```json
{
  "survey_id": 1,
  "invitation_id": 10,
  "status": "opened"
}
```

Behavior:

- API хэширует raw token из URL;
- ищет invitation по `survey_id` и `token_hash`;
- проверяет, что invitation не revoked, не used и не expired;
- если invitation был в статусе `sent`, переводит его в `opened`.

Errors:

| Status | Meaning |
|---:|---|
| `404` | Invitation not found |
| `409` | Invitation revoked |
| `409` | Invitation already used |
| `409` | Invitation expired |

Notes:

- В текущей реализации expired/revoked/used возвращаются как `409 Conflict`.
- `410 Gone` сейчас не используется.
- Revoked invitation сейчас не маскируется под `404`, а возвращается как `409 Conflict`.

---

### POST /s/{survey_id}/{token}

Отправить ответы по public invite link.

Path params:

| Param | Type | Description |
|---|---:|---|
| `survey_id` | integer | ID survey |
| `token` | string | Raw invitation token из ссылки |

Request:

```json
{
  "answers": {
    "q1": "Да",
    "q2": 5
  }
}
```

Request fields:

| Field | Type | Required | Description |
|---|---:|---:|---|
| `answers` | object | yes | Ответы пользователя |

Validation:

- `answers` должен быть object;
- `answers` не должен быть пустым.

Response:

```json
{
  "ok": true,
  "response_id": 1
}
```

Behavior:

- API хэширует raw token из URL;
- ищет invitation по `survey_id` и `token_hash`;
- проверяет, что invitation не revoked, не used и не expired;
- создаёт `Response`;
- сохраняет `answers`;
- обновляет invitation:
  - `used_at = now()`;
  - `status = "completed"`.

Errors:

| Status | Meaning |
|---:|---|
| `404` | Invitation not found |
| `409` | Invitation revoked |
| `409` | Invitation already used |
| `409` | Invitation expired |
| `422` | Некорректный request payload |

Notes:

- В текущем MVP submit не выдаёт promo code.
- Promo codes не входят в актуальный API contract.
- Invalid payload в FastAPI обычно возвращается как `422`, не `400`.

---

## Not Implemented / Future API

Эти endpoints или части контракта не входят в текущий MVP:

```text
POST /bot/users/delete_me
GET /operator/surveys/{survey_id}/stats
promo code issuance on response submit
```

Планируемые будущие возможности:

- user deletion/anonymization;
- survey statistics endpoint;
- real Telegram Bot API integration;
- production-grade auth/authz;
- promo code pool and issuance;
- stricter response schema validation;
- idempotent public submit;
- rate limiting for public endpoints.