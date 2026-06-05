# SurveyGate — Architectural Decisions

Документ фиксирует ключевые архитектурные решения SurveyGate MVP.

Формат: ADR-lite.  
Цель — коротко объяснить, почему модель устроена именно так.

---

## ADR-001: Split users and user_identities

### Decision

Разделить основную пользовательскую сущность `users` и внешнюю идентичность `user_identities`.

`users` хранит профиль респондента:

- city;
- age;
- has_children;
- is_deleted;
- deleted_at.

`user_identities` хранит внешний идентификатор:

- telegram_id.

### Why

Так проще отделить анкетные/аналитические данные от внешней идентичности пользователя.

Это помогает:

- подготовить основу для будущей анонимизации;
- не смешивать профиль респондента и Telegram identity;
- потенциально поддержать другие identity providers в будущем;
- сохранить историю invitations/responses без жёсткой привязки к Telegram ID.

### Trade-offs

- Модель становится чуть сложнее.
- Для поиска пользователя по `telegram_id` нужен join или отдельный lookup через `user_identities`.

### Current status

Реализовано в текущем MVP.

---

## ADR-002: Store token_hash instead of raw token

### Decision

Не хранить raw invitation token в базе.

При создании invitation система:

1. генерирует raw token;
2. формирует public invite link;
3. сохраняет в БД только `token_hash`.

### Why

Invitation token — это bearer-secret.

Если raw token хранить в базе, то при утечке базы злоумышленник сможет открыть или отправить survey response от имени пользователя.

Хранение только hash снижает ущерб от утечки базы.

### Current implementation

В текущем MVP используется:

```text
raw token -> HMAC-SHA256(token, SECRET_KEY) -> token_hash
```

### Trade-offs

- Raw token невозможно восстановить из базы.
- Public invite link можно показать только в момент создания invitation.
- Для resend/reissue нужно создавать новый token.

### Current status

Реализовано в текущем MVP.

---

## ADR-003: Partial unique index for active invitations

### Decision

Разрешить хранить историю invitations, но запретить два активных invitation для одного пользователя на один survey.

Текущий invariant:

```sql
UNIQUE (survey_id, user_id)
WHERE revoked_at IS NULL AND used_at IS NULL
```

### Why

Нужно избежать ситуации, когда у одного пользователя одновременно есть две валидные ссылки на один и тот же survey.

При этом история сохраняется:

- старые revoked invitations остаются в базе;
- completed invitations остаются в базе;
- resend/reissue создаёт новый invitation, а старый отзывается.

### Trade-offs

Такой constraint запрещает только два активных invitation.

Он не запрещает пользователю пройти один survey повторно после completion, если будет создан новый invitation.

Если бизнес-правило должно быть строже, нужно добавить отдельный constraint:

```sql
UNIQUE (survey_id, user_id)
```

на уровне `responses` или дополнительную проверку в сервисном слое.

### Current status

Реализовано в текущем MVP.

---

## ADR-004: Split Invitation and InvitationDeliveryJob

### Decision

Разделить бизнес-сущность invitation и техническую задачу доставки.

`Invitation` отвечает на вопрос:

```text
Может ли этот пользователь открыть и пройти этот survey?
```

`InvitationDeliveryJob` отвечает на вопрос:

```text
Нужно ли отправить сообщение, было ли оно отправлено, были ли ошибки доставки?
```

### Why

Доставка сообщения — это технический процесс, который может:

- падать;
- повторяться;
- выполняться асинхронно;
- иметь свои статусы;
- иметь свои ошибки;
- обрабатываться worker-ом.

Если смешать delivery state с invitation state, модель быстро станет грязной.

Разделение позволяет независимо развивать:

- бизнес-логику invitation;
- retry/backoff;
- worker recovery;
- monitoring доставки;
- разные delivery channels.

### Trade-offs

- Появляется дополнительная таблица.
- Нужно синхронизировать статусы invitation и delivery job.
- Нужно следить за консистентностью между PostgreSQL и Redis/RQ.

### Current status

Реализовано в текущем MVP.

---

## ADR-005: Use Redis/RQ for asynchronous delivery

### Decision

Выносить доставку invitation messages из request/response цикла в Redis/RQ queue.

Operator endpoint создаёт invitations и delivery jobs, после чего jobs ставятся в очередь.

Worker обрабатывает delivery jobs отдельно.

### Why

Отправка сообщений не должна блокировать HTTP-запрос оператора.

Очередь позволяет:

- быстро отвечать operator API;
- обрабатывать доставку асинхронно;
- в будущем добавить retry/backoff;
- масштабировать worker-ы отдельно от API;
- отделить создание invitation от фактической отправки сообщения.

### Important invariant

PostgreSQL остаётся source of truth.

Redis/RQ — это delivery transport, а не основное хранилище состояния.

Persistent state хранится в:

```text
invitation_delivery_jobs
```

### Trade-offs

- Возможна рассинхронизация: запись в PostgreSQL создана, но enqueue в Redis не произошёл.
- Для production нужен outbox/sweeper или другой recovery mechanism.
- Нужно отдельно запускать worker.

### Current status

Реализовано в MVP на базовом уровне.

Реальная Telegram-доставка пока заменена stub sender.

---

## ADR-006: JSON-based segmentation

### Decision

Хранить segment filters как JSONB-дерево.

Пример:

```json
{
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
```

### Why

Для MVP JSON DSL даёт хорошую гибкость.

Он позволяет:

- быстро добавлять новые типы условий;
- хранить сегмент как переиспользуемую сущность;
- валидировать segment перед выполнением;
- компилировать segment в SQLAlchemy query;
- не создавать сложную нормализованную модель rule/group tables на раннем этапе.

### Trade-offs

- Сложнее делать аналитику по структуре сегментов.
- Нужно аккуратно валидировать входной JSON.
- Оптимизация сложнее, чем у полностью нормализованной схемы.
- DSL требует понятного набора разрешённых fields/operators.

### Current status

Реализовано в текущем MVP.

---

## ADR-007: Use constrained statuses where useful, but keep workflow lightweight

### Decision

Использовать закрытые наборы статусов там, где это уже полезно, но не усложнять MVP полноценными workflow tables.

Текущий статус:

- `Survey.status` — string с DB check constraint;
- `InvitationDeliveryJob.status` — PostgreSQL enum через SQLAlchemy enum;
- `Invitation.status` — string без DB-level constraint.

### Why

Для MVP не нужна отдельная lookup/workflow-модель.

При этом для некоторых сущностей полезно ограничить возможные значения, чтобы не получить мусорные статусы в БД.

### Trade-offs

- `Invitation.status` пока слабее защищён на уровне БД.
- Workflow transitions контролируются в приложении, а не в базе.
- Если статусы начнут усложняться, string/enum может стать неудобным.

### Recommendation

Добавить DB check constraint для `invitations.status`:

```sql
CHECK (status IN ('queued', 'sent', 'opened', 'completed', 'revoked'))
```

Не хранить `expired` как обязательный persisted status.  
Лучше считать его derived state:

```text
expires_at <= now
AND used_at IS NULL
AND revoked_at IS NULL
```

### Current status

Частично реализовано.

---

## ADR-008: Promo codes are out of current MVP scope

### Decision

Не включать promo code pool и promo issuance в текущий MVP.

### Why

Основной фокус SurveyGate сейчас:

- user profile;
- segmentation;
- survey sends;
- invitations;
- tokenized public links;
- responses;
- async delivery jobs.

Promo codes — отдельная доменная подсистема со своими инвариантами:

- pool of codes;
- code reservation;
- code issuance;
- concurrent issuance;
- audit;
- uniqueness per user/survey.

Добавлять её в текущий MVP преждевременно.

### Current status

Не реализовано.

### Future option

Если промокоды вернутся в roadmap, их стоит описать отдельным ADR:

```text
ADR-XXX: Promo code pool and issuance
```

Возможная будущая модель:

```text
promo_code_pool
promo_issuances
```

Возможный concurrent issuance pattern:

```sql
SELECT *
FROM promo_code_pool
WHERE survey_id = :survey_id
  AND status = 'available'
FOR UPDATE SKIP LOCKED
LIMIT 1;
```

Но это future extension, а не текущая архитектура.

---

# Summary

Ключевые решения текущего SurveyGate MVP:

1. `users` отделены от `user_identities`.
2. Raw invitation tokens не хранятся в базе.
3. Partial unique index запрещает два активных invitation на один survey/user.
4. `Invitation` отделён от `InvitationDeliveryJob`.
5. Redis/RQ используется для асинхронной доставки.
6. PostgreSQL остаётся source of truth.
7. Segments хранятся как JSONB DSL.
8. Promo codes не входят в текущий MVP.