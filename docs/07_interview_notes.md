# SurveyGate — Interview Notes

Документ помогает кратко и уверенно объяснить SurveyGate на собеседовании.

SurveyGate стоит презентовать как backend-MVP, а не как production-ready коммерческий продукт.

---

## 1. Короткий pitch

SurveyGate — это backend-MVP сервиса для рекрутинга UX-респондентов и рассылки опросов по сегментам.

Проект позволяет:

- регистрировать пользователей через bot-like API;
- хранить профили респондентов;
- создавать surveys;
- создавать JSON-сегменты;
- выбирать пользователей по сегменту;
- генерировать одноразовые invitation links;
- хранить только hash токена;
- создавать delivery jobs;
- отправлять jobs в Redis/RQ queue;
- принимать ответы через public invite link.

Главная идея проекта: показать не CRUD, а цельный backend-flow от сегментации пользователя до отправки ответа.

---

## 2. Версия на 60 секунд

SurveyGate — это backend-MVP для автоматизации рекрутинга UX-респондентов.

Проблема в том, что исследователи часто вручную фильтруют пользователей, рассылают ссылки и отслеживают ответы через таблицы, формы и чаты. Я сделал API, где можно хранить профили пользователей, создавать опросы, описывать сегменты через JSON-фильтры, генерировать одноразовые invite links и принимать ответы через публичные tokenized URLs.

Важное архитектурное решение — raw invitation token не хранится в базе. В БД сохраняется только hash токена, поэтому при утечке базы нельзя сразу получить валидные ссылки на опросы.

Второе важное решение — разделение `Invitation` и `InvitationDeliveryJob`. `Invitation` — это бизнес-сущность, которая даёт пользователю доступ к survey. `InvitationDeliveryJob` — техническая задача доставки, которую можно обрабатывать worker-ом, retry-ить и логировать отдельно.

Сейчас это MVP: реальная Telegram-доставка заменена stub-логикой, но уже есть Redis/RQ-инфраструктура, public token flow, миграции, тесты и roadmap до production-ready состояния.

---

## 3. Основной demo-flow

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
-> repeated submit is rejected
```

Что важно подчеркнуть:

- segment хранится как JSON;
- JSON валидируется;
- segment компилируется в SQLAlchemy query;
- invitation получает одноразовый token;
- в БД хранится только `token_hash`;
- delivery вынесена в `InvitationDeliveryJob`;
- Redis/RQ используется для асинхронной доставки;
- public submit помечает invitation как completed;
- повторный submit по тому же token блокируется.

---

## 4. Архитектура

```text
Operator / Bot / Public user
        |
        v
FastAPI application
        |
        +--> PostgreSQL
        |       - users
        |       - user identities
        |       - surveys
        |       - segments
        |       - survey sends
        |       - invitations
        |       - invitation delivery jobs
        |       - responses
        |
        +--> Redis / RQ
                - delivery queue
                - worker processes delivery jobs
```

Структурно:

- routers отвечают за API endpoints;
- services содержат бизнес-логику;
- SQLAlchemy models описывают таблицы;
- Alembic управляет миграциями;
- Redis/RQ используется для фоновой обработки delivery jobs.

---

## 5. Основные сущности

### User

Респондент, которого можно пригласить на survey.

### UserIdentity

Внешняя идентичность пользователя, сейчас — Telegram ID.

### Segment

Переиспользуемый JSON-фильтр для выбора пользователей.

### Survey

Опрос или исследование.

### SurveySend

Конкретный запуск рассылки survey по segment.

### Invitation

Бизнес-приглашение пользователя пройти survey.

### InvitationDeliveryJob

Техническая задача доставки invitation message.

### Response

Ответ пользователя на survey.

---

## 6. Почему JSON-сегменты?

Я выбрал JSON-based segmentation как прагматичное MVP-решение.

Плюсы:

- гибко;
- быстро реализовать;
- удобно передавать через API;
- можно поддержать вложенные `AND` / `OR`;
- можно валидировать перед выполнением;
- можно компилировать в SQLAlchemy query.

Минусы:

- сложнее анализировать напрямую через SQL;
- нужна строгая валидация;
- при росте DSL может стать сложнее поддерживать;
- нормализованные rule tables были бы строже, но тяжелее для MVP.

Как это работает:

```text
operator sends JSON filters
-> validate_segment_tree checks structure
-> compile_segment_query builds SQLAlchemy query
-> query returns matching users
```

Важный момент: система не исполняет raw SQL из JSON. Она принимает только разрешённые поля и операторы, а затем строит SQLAlchemy expressions.

---

## 7. Почему token_hash вместо raw token?

Invitation link работает как bearer-secret: у кого есть ссылка, тот может открыть public invite flow.

Поэтому raw token нельзя хранить в базе.

Flow:

```text
generate raw token
-> return raw token only in invite link
-> store token_hash in database
-> hash incoming token
-> compare hash with stored token_hash
```

Это снижает риск при утечке базы: из `token_hash` нельзя напрямую восстановить валидную ссылку.

---

## 8. Почему Invitation и DeliveryJob разделены?

Потому что они отвечают на разные вопросы.

`Invitation` отвечает:

```text
Есть ли у пользователя доступ к этому survey?
Активен ли invite?
Он completed, revoked или expired?
```

`InvitationDeliveryJob` отвечает:

```text
Создана ли задача доставки?
Поставлена ли она в очередь?
Обработал ли её worker?
Была ли ошибка?
Нужно ли retry?
```

Это разделение полезно, потому что доставка ненадёжна по природе: Telegram, Redis, сеть или worker могут падать. Бизнес-состояние invitation не должно жёстко зависеть от одной попытки доставки.

---

## 9. Почему Redis/RQ?

Redis/RQ нужен, чтобы вынести доставку сообщений из HTTP request/response цикла.

Без очереди:

```text
operator sends invitations
-> API синхронно отправляет все сообщения
-> request становится долгим и хрупким
```

С очередью:

```text
operator sends invitations
-> API создаёт invitations и delivery jobs
-> jobs попадают в Redis/RQ
-> worker обрабатывает доставку отдельно
```

Почему RQ, а не Celery:

- проще настроить;
- проще объяснить;
- достаточно для MVP;
- меньше инфраструктурной сложности.

Trade-off: для production нужно добавить retry/backoff, dead-letter handling, sweeper/outbox и observability.

---

## 10. Что значит статус `queued`?

`queued` означает, что invitation создан и delivery job поставлена в очередь, но worker ещё не отметил invitation как успешно доставленный.

Типичный flow:

```text
queued -> sent -> opened -> completed
```

В demo public link возвращается прямо из API, поэтому его можно открыть даже в статусе `queued`.

В production пользователь должен получать ссылку только после фактической доставки через Telegram.

---

## 11. Quality gate

Текущая проверка проекта:

```bash
poetry run ruff check .
poetry run python -m pytest
```

Что можно сказать:

- проект покрыт тестами на core-flow;
- используется ruff;
- есть Alembic migrations;
- миграционные файлы можно исключать из ruff, потому что это исторические generated scripts.

---

## 12. Что пока не production-ready

Проект честно позиционируется как MVP.

Пока не хватает:

- реальной Telegram Bot API интеграции;
- нормальной operator auth вместо общего `X-API-Key`;
- защиты bot endpoints;
- retry/backoff/dead-letter механизма;
- outbox/sweeper для восстановления очереди;
- rate limiting;
- audit log;
- observability;
- user deletion/anonymization policy;
- production Dockerfile для API/worker;
- строгой схемы survey answers.

Хорошая формулировка:

> Я намеренно презентую проект как backend-MVP. Он показывает архитектурные решения и основной flow, но я отдельно документирую, что нужно добавить перед production.

---

## 13. Production roadmap

Перед production я бы добавил:

### Security

- operator authentication;
- roles/permissions;
- audit log;
- bot endpoint protection;
- rate limiting;
- protected Swagger/OpenAPI.

### Delivery reliability

- real Telegram Bot API adapter;
- timeouts;
- retry with backoff;
- dead-letter handling;
- manual retry;
- worker as production service.

### Queue reliability

- PostgreSQL as source of truth;
- sweeper for pending jobs;
- stale processing job recovery;
- outbox pattern или аналог.

### Idempotency

- `Idempotency-Key` для bulk send;
- защита от duplicate send;
- atomic public submit;
- graceful handling of `IntegrityError`.

### Observability

- structured logs;
- correlation IDs;
- queue metrics;
- worker heartbeat;
- alerts;
- error tracking.

### Data protection

- consent;
- deletion/anonymization;
- retention policy;
- restricted operator access;
- secure backups.

---

## 14. Частые вопросы на собеседовании

### Почему FastAPI?

Потому что это современный Python framework для API-first backend: async support, dependency injection, Pydantic, automatic OpenAPI и удобная структура для MVP.

### Почему async SQLAlchemy?

Проект I/O-bound: база, Redis, в будущем Telegram API. Async SQLAlchemy хорошо подходит под такую модель, хотя добавляет сложность с sessions, lazy loading и тестами.

### Почему не Django?

Django был бы хорош для admin-heavy продукта. Но здесь я хотел показать API-first backend на FastAPI, async database access, queues и явное разделение слоёв.

### Почему JSON-сегменты безопасны?

Потому что система не принимает raw SQL. JSON валидируется по whitelist полей и операторов, а затем компилируется в SQLAlchemy expressions.

### Что будет, если Redis упадёт?

В MVP enqueue failure логируется. В production я бы считал PostgreSQL source of truth и добавил sweeper/requeue, который находит pending jobs и повторно ставит их в очередь.

### Можно ли отправить response дважды?

Нет. После successful submit invitation получает `used_at` и статус `completed`. Повторный submit возвращает ошибку. Дополнительно есть constraint на один response per invitation.

### Какие главные trade-offs?

- JSON segmentation гибкая, но сложнее для анализа и оптимизации.
- RQ проще Celery, но требует production-hardening.
- `X-API-Key` достаточно для MVP, но не для production.
- Raw invite links удобно возвращать в demo, но не стоит делать так в production.
- JSONB answers гибкие, но требуют schema validation перед production.

---

## 15. Сильные стороны проекта

Стоит подчеркнуть:

- это не просто CRUD;
- есть понятная доменная проблема;
- есть цельный backend-flow;
- есть JSON DSL для сегментов;
- есть token hashing;
- есть public invite flow;
- есть разделение business и delivery сущностей;
- есть Redis/RQ pipeline;
- есть Alembic migrations;
- есть tests + ruff;
- есть честный production roadmap.

---

## 16. Слабые места, о которых лучше говорить честно

- нет real Telegram adapter;
- нет UI;
- ограниченное покрытие тестами;
- нет полноценной auth model;
- нет retry/backoff;
- нет observability stack;
- нет полноценной anonymization policy;
- нет production deployment setup.

Хорошая формулировка:

> Я не пытаюсь выдать MVP за production. Для меня ценность проекта в том, что он показывает backend-мышление: модель данных, API flow, безопасность токенов, сегментацию, очередь доставки и понимание production gaps.

---

## 17. Личное позиционирование

Этот проект хорошо связан с моим прошлым опытом UX-исследователя.

Я понимаю доменную проблему, потому что сам сталкивался с рекрутингом респондентов, сегментацией пользователей, рассылками и ручным трекингом ответов.

Но в этом проекте я фокусируюсь именно на backend implementation:

- API design;
- data model;
- async database access;
- migrations;
- JSON segmentation;
- invitation security;
- delivery architecture;
- tests.

Хорошая формулировка:

> Мой UX research background помогает мне понимать продуктовую задачу, но SurveyGate я использую как backend-проект: здесь я показываю API-дизайн, модель данных, сегментацию, token security, очередь доставки и работу с PostgreSQL/Redis.