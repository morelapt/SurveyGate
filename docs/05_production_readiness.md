# SurveyGate — Production Readiness Roadmap

SurveyGate сейчас является backend-MVP для демонстрации архитектуры и обсуждения на собеседовании.

Проект уже показывает ключевой flow:

- регистрация пользователя;
- заполнение профиля;
- создание survey;
- создание JSON-сегмента;
- рассылка invitations;
- постановка delivery jobs в Redis/RQ;
- обработка worker-ом;
- открытие публичной ссылки;
- отправка response.

Но проект пока не готов к коммерческому production-запуску.

---

## 1. Безопасность API

### Текущее состояние

- operator API защищён одним `X-API-Key`;
- bot-like endpoints напрямую принимают пользовательские данные;
- public invite endpoints доступны по bearer-ссылке.

### Что нужно добавить

- полноценную авторизацию операторов;
- роли и права доступа;
- защиту bot endpoints через service token или проверку Telegram webhook;
- rate limiting для operator/bot/public endpoints;
- audit log действий оператора;
- настройку CORS, TrustedHost и security headers;
- отключение или защиту Swagger/OpenAPI в production.

### Почему важно

Операторские endpoints могут создавать опросы, сегменты и массовые рассылки. В production одного общего API-ключа недостаточно.

---

## 2. Секреты и чувствительные данные

### Текущее состояние

- настройки хранятся через `.env`;
- raw invitation token не хранится в БД;
- send endpoint возвращает invite links для demo-flow;
- доставка сообщений пока заменена stub-логикой.

### Что нужно добавить

- хранение секретов через инфраструктурный secret manager;
- разделение dev/staging/prod настроек;
- запрет логирования raw tokens, API keys, `DATABASE_URL`, `SECRET_KEY`;
- маскирование `telegram_id` в логах;
- отказ от возврата raw invite links из bulk API в production;
- контроль утечек токенов через логи, referrer, debug output.

### Почему важно

Invite link — это bearer-secret. Любой, у кого есть ссылка, может открыть public invite flow.

---

## 3. Персональные данные и приватность

### Текущее состояние

Проект хранит:

- профиль пользователя;
- Telegram ID;
- ответы на опросы;
- текст сообщения в delivery jobs.

### Что нужно добавить

- privacy policy;
- согласие на обработку данных;
- полноценный `/delete_me` или anonymization flow;
- retention policy для responses и delivery jobs;
- ограничение доступа операторов к персональным данным;
- защиту backup-ов;
- audit доступа к данным.

### Почему важно

SurveyGate работает с данными респондентов, поэтому production-версия должна явно решать вопросы хранения, удаления и доступа к данным.

---

## 4. Надёжная доставка сообщений

### Текущее состояние

- есть `InvitationDeliveryJob`;
- есть Redis/RQ queue;
- worker обрабатывает delivery jobs;
- реальная Telegram-доставка пока не реализована.

### Что нужно добавить

- адаптер к реальному Telegram Bot API;
- timeouts для внешних запросов;
- обработку Telegram `429 Too Many Requests`;
- retry с backoff;
- dead-letter handling;
- ручной retry failed jobs;
- запуск worker-а как отдельного production-сервиса;
- отображение ошибок доставки оператору.

### Почему важно

Главный production-риск — не создание invitations, а их реальная и проверяемая доставка пользователям.

---

## 5. Надёжность очереди

### Текущее состояние

- delivery jobs создаются в PostgreSQL;
- после commit они ставятся в Redis/RQ;
- PostgreSQL хранит persistent state;
- Redis/RQ используется как очередь выполнения.

### Потенциальная проблема

Может произойти сбой между commit в БД и enqueue в Redis:

```text
PostgreSQL commit успешен
Redis enqueue не произошёл
delivery job есть в БД, но отсутствует в очереди
```

### Что нужно добавить

- считать PostgreSQL source of truth;
- использовать Redis/RQ только как transport layer;
- sweeper/requeue для pending jobs;
- requeue зависших queued/processing jobs;
- outbox pattern или аналогичный recovery-механизм;
- метрики очереди;
- worker heartbeat;
- алерты на stuck jobs.

### Почему важно

Система должна гарантировать, что созданные delivery jobs либо попадут в worker, либо будут явно помечены как failed/stuck.

---

## 6. Идемпотентность и race conditions

### Production-риски

- оператор дважды нажал “send”;
- HTTP-запрос повторился после timeout;
- два worker-а обрабатывают одну job;
- пользователь дважды отправил response;
- invitation был revoked, пока delivery job уже стояла в очереди.

### Что нужно добавить

- `Idempotency-Key` для bulk send операций;
- защиту от duplicate send;
- атомарный public submit;
- row locking при submit;
- корректную обработку `IntegrityError`;
- атомарные переходы статусов delivery jobs;
- idempotent worker operations;
- понятные `409 Conflict` вместо случайных `500`.

### Почему важно

Большая часть production-багов в таких системах появляется из-за retry, дублей и частичных сбоев.

---

## 7. Валидация публичных ответов

### Текущее состояние

- ответы хранятся как JSONB;
- строгой схемы survey answers пока нет.

### Что нужно добавить

- схему вопросов survey;
- валидацию `answers` перед сохранением;
- ограничение размера request body;
- rate limiting public endpoints;
- защиту от повторной отправки;
- понятные состояния для expired/revoked/used invitation.

### Почему важно

JSONB удобен для MVP, но production-данные должны быть валидными и ограниченными по размеру.

---

## 8. Deployment

### Текущее состояние

- Docker Compose поднимает PostgreSQL и Redis;
- API запускается локально через Uvicorn;
- worker запускается отдельно через RQ CLI;
- production API/worker containers пока нет.

### Что нужно добавить

- Dockerfile;
- отдельный API container;
- отдельный worker container;
- migration job;
- запуск без `--reload`;
- закрытый доступ к PostgreSQL и Redis;
- reverse proxy;
- HTTPS;
- healthchecks;
- backup/restore process;
- rollback strategy;
- staging environment.

### Почему важно

Production должен запускаться повторяемо и безопасно, а не вручную как локальный dev-стенд.

---

## 9. Observability

### Текущее состояние

Есть базовые endpoints:

```text
/health
/health/db
```

### Что нужно добавить

- `/health/live`;
- `/health/ready`;
- Redis health check;
- worker heartbeat;
- structured logs;
- request/correlation IDs;
- API latency/error metrics;
- queue metrics:
  - pending;
  - queued;
  - processing;
  - sent;
  - failed;
- alerts на failed jobs, растущую очередь и dead workers;
- error tracking, например Sentry.

### Почему важно

Здоровый API ещё не означает, что invitations реально доставляются. Нужно видеть состояние worker-а и очереди.

---

## 10. Тесты и CI

### Текущее состояние

В проекте уже есть тесты для части core-flow.

### Что нужно добавить

Тесты на:

- полный flow:
  - register user;
  - update profile;
  - create survey;
  - create segment;
  - preview segment;
  - send invitations;
  - process delivery;
  - open invite;
  - submit response;
- expired/revoked/used invitations;
- duplicate submit;
- duplicate send;
- Redis failure;
- Telegram failure;
- invalid segment DSL;
- invalid device/service codes;
- auth negative cases;
- миграции на чистой БД.

CI:

- ruff;
- pytest;
- migration smoke test;
- Docker build;
- basic startup/import check.

### Почему важно

MVP уже демонстрирует архитектуру, но production требует уверенности, что critical flows не ломаются при изменениях.

---

## 11. Data model hardening

Перед production стоит добавить или проверить:

```sql
CHECK (invitations.status IN ('queued', 'sent', 'opened', 'completed', 'revoked'));
```

Если бизнес-правило требует один response на пользователя в рамках survey:

```sql
UNIQUE (survey_id, user_id)
```

Также стоит рассмотреть:

- единый тип `bigint` для `telegram_id`;
- поле `rq_job_id` в `invitation_delivery_jobs`;
- дополнительные индексы для public token lookup;
- retention policy для старых delivery jobs.

---

## Рекомендуемый порядок работ

1. Нормальная авторизация operator API.
2. Защита bot endpoints.
3. Реальный Telegram Bot API adapter.
4. Rate limiting.
5. Атомарный public submit.
6. Retry/backoff для delivery jobs.
7. Sweeper/outbox для восстановления очереди.
8. API и worker containers.
9. Readiness/liveness checks.
10. Structured logs и queue metrics.
11. `/delete_me` / anonymization policy.
12. CI: tests, lint, migrations, Docker build.
13. Survey answer schema validation.
14. Survey statistics / operator dashboard.

---

## Summary

SurveyGate уже полезен как backend-MVP для демонстрации архитектуры.

Но перед production нужно усилить:

- безопасность;
- доставку сообщений;
- восстановление очереди;
- идемпотентность;
- валидацию данных;
- deployment;
- observability;
- privacy;
- тесты.

Следующий инженерный шаг — не добавлять новые бизнес-фичи, а сделать текущий flow надёжным, наблюдаемым и безопасным.