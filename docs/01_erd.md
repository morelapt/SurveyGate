# ERD & Database Constraints (PostgreSQL)

Этот документ описывает модель данных сервиса рассылки мини-опросов через Telegram-бота:
пользователи → сегменты → рассылки → инвайты → ответы → выдача промокодов.

Фокус:
- одноразовые токены
- запрет двух активных инвайтов
- запрет двух промокодов на survey
- конкурентная выдача из пула
- корректная анонимизация (/delete_me)

---

## ERD (Mermaid)

## High-level Domain ERD


erDiagram
  USERS ||--o| USER_IDENTITIES : has_identity
  USERS ||--o{ USER_DEVICES : has
  USERS ||--o{ USER_SERVICES : uses

  DEVICES ||--o{ USER_DEVICES : in
  SERVICES ||--o{ USER_SERVICES : in

  USERS ||--o{ INVITATIONS : receives
  SURVEYS ||--o{ INVITATIONS : sends
  SURVEY_SENDS ||--o{ INVITATIONS : creates

  INVITATIONS ||--o| RESPONSES : results_in

  SEGMENTS ||--o{ SURVEY_SENDS : used_in
  SURVEYS  ||--o{ SURVEY_SENDS : has

  SURVEYS ||--o{ PROMO_CODE_POOL : has_pool
  PROMO_CODE_POOL ||--o| PROMO_ISSUANCES : may_be_issued
  INVITATIONS ||--o| PROMO_ISSUANCES : issues_code
  USERS ||--o{ PROMO_ISSUANCES : receives_code


Enum-типы (PostgreSQL)

Используются enum-типы для закрытых наборов статусов:

survey_status: draft | active | closed

invitation_status: sent | opened | completed | expired | revoked

promo_code_status: available | reserved | issued

Плюсы:

защита от некорректных значений

проще аналитика

значения редко меняются

Если статусы станут workflow-ом — можно вынести в lookup-таблицы.

Core Invariants
Completion

Истина completion = наличие записи в responses.

responses.invitation_id UNIQUE

invitations.used_at проставляется при submit

Один активный инвайт

Частичный уникальный индекс:

UNIQUE (survey_id, user_id)
WHERE revoked_at IS NULL

Один промокод на user + survey

Через promo_issuances:

UNIQUE(invitation_id)

UNIQUE(promo_code_id)

UNIQUE(survey_id, user_id)

Индексы
Users / сегменты

users(city)

users(age)

M2M

user_devices(device_id, user_id)

user_services(service_id, user_id)

Tokens

invitations(token_hash) UNIQUE

Promo

promo_code_pool(code) UNIQUE

promo_code_pool(survey_id, status, duration_months)

promo_issuances(survey_id, user_id) UNIQUE

/delete_me Policy
Цель

Удалить PII, но сохранить:

статистику

историю

запреты на повторную выдачу

Действия

users:

is_deleted = true

deleted_at = now()

user_identities:

deleted_at = now() или DELETE

user_devices / user_services:

удалить строки

invitations / responses / promo_issuances:

НЕ удаляются

## Logical Data Model (Detailed)

erDiagram
  USERS ||--o| USER_IDENTITIES : has_identity
  USERS ||--o{ USER_DEVICES : has
  USERS ||--o{ USER_SERVICES : uses

  DEVICES ||--o{ USER_DEVICES : in
  SERVICES ||--o{ USER_SERVICES : in

  USERS ||--o{ INVITATIONS : receives
  SURVEYS ||--o{ INVITATIONS : sends
  SURVEY_SENDS ||--o{ INVITATIONS : creates

  INVITATIONS ||--o| RESPONSES : results_in

  SEGMENTS ||--o{ SURVEY_SENDS : used_in
  SURVEYS  ||--o{ SURVEY_SENDS : has

  SURVEYS ||--o{ PROMO_CODE_POOL : has_pool
  PROMO_CODE_POOL ||--o| PROMO_ISSUANCES : may_be_issued
  INVITATIONS ||--o| PROMO_ISSUANCES : issues_code
  USERS ||--o{ PROMO_ISSUANCES : receives_code

  USERS {
    uuid id PK
    text city
    int age
    boolean is_deleted
    timestamptz deleted_at
    timestamptz created_at
    timestamptz updated_at
  }

  USER_IDENTITIES {
    uuid user_id PK,FK
    bigint telegram_id "UNIQUE"
    text language
    text source
    timestamptz created_at
    timestamptz deleted_at
  }

  DEVICES {
    smallint id PK
    text code "UNIQUE"
    text title
  }

  SERVICES {
    smallint id PK
    text code "UNIQUE"
    text title
  }

  USER_DEVICES {
    uuid user_id FK
    smallint device_id FK
    timestamptz created_at
    "PK(user_id, device_id)"
  }

  USER_SERVICES {
    uuid user_id FK
    smallint service_id FK
    timestamptz created_at
    "PK(user_id, service_id)"
  }

  SURVEYS {
    uuid id PK
    text title
    survey_status status "draft|active|closed"
    timestamptz starts_at
    timestamptz ends_at
    jsonb public_schema
    timestamptz created_at
  }

  SEGMENTS {
    uuid id PK
    text name
    jsonb filters "city/age/devices/services/etc"
    timestamptz created_at
  }

  SURVEY_SENDS {
    uuid id PK
    uuid survey_id FK
    uuid segment_id FK
    text message_template
    timestamptz sent_at
    uuid created_by
  }

  INVITATIONS {
    uuid id PK
    uuid survey_id FK
    uuid user_id FK
    uuid send_id FK
    bytea token_hash "UNIQUE"
    timestamptz created_at
    timestamptz sent_at
    timestamptz expires_at
    timestamptz used_at
    timestamptz revoked_at
    int resend_count
    invitation_status status "sent|opened|completed|expired|revoked"
  }

  RESPONSES {
    uuid id PK
    uuid invitation_id FK "UNIQUE"
    uuid survey_id FK
    uuid user_id FK
    jsonb payload
    timestamptz submitted_at
  }

  PROMO_CODE_POOL {
    uuid id PK
    uuid survey_id FK
    text code "UNIQUE"
    smallint duration_months "1|2"
    promo_code_status status "available|reserved|issued"
    timestamptz reserved_at
    timestamptz issued_at
    uuid reserved_by_invitation_id "UNIQUE nullable"
    timestamptz created_at
  }

  PROMO_ISSUANCES {
    uuid id PK
    uuid promo_code_id FK "UNIQUE"
    uuid invitation_id FK "UNIQUE"
    uuid survey_id FK
    uuid user_id FK
    timestamptz issued_at
  }
