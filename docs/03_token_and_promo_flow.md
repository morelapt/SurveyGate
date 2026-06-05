# SurveyGate — Token & Public Invite Flow

Документ описывает актуальный token flow в SurveyGate MVP.

Promo codes в текущем MVP не реализованы, поэтому не входят в актуальный flow.

---

## Что такое invitation token

Invitation token — это одноразовый bearer-secret, связанный с конкретным `Invitation`.

Он используется в публичной ссылке:

```text
/s/{survey_id}/{token}
```

Token даёт пользователю право:

1. открыть публичную страницу invitation;
2. отправить response по этому invitation.

---

## Raw token не хранится в базе

При создании invitation система генерирует raw token.

В базе хранится только:

```text
invitations.token_hash
```

Raw token используется только для формирования публичной ссылки.

Текущий механизм:

```text
raw token -> HMAC-SHA256(token, SECRET_KEY) -> token_hash
```

Это снижает риск при утечке базы: из `token_hash` нельзя напрямую восстановить raw token.

---

## Какие поля invitation участвуют в token flow

В token/public flow используются поля:

```text
token_hash
expires_at
used_at
revoked_at
status
```

Смысл полей:

| Field | Meaning |
|---|---|
| `token_hash` | Hash raw token из публичной ссылки |
| `expires_at` | Время истечения invitation |
| `used_at` | Время successful submit |
| `revoked_at` | Время отзыва invitation |
| `status` | Текущий application-level статус invitation |

---

## TTL

TTL задаётся при запуске рассылки через `ttl_days`.

В текущем MVP:

```text
expires_at = now + ttl_days
```

То есть TTL считается от момента создания invitations в рамках send flow, а не от фактического `sent_at`.

Default:

```text
ttl_days = 14
```

Expired invitation определяется так:

```text
expires_at <= now
```

В текущей реализации expired invitation возвращает:

```text
409 Conflict
```

А не:

```text
410 Gone
```

Если хочется более REST-семантичного поведения, в будущем можно заменить expired case на `410 Gone`.

---

## Send flow

Send flow запускается через operator endpoint:

```text
POST /operator/surveys/{survey_id}/send_invitations
```

Упрощённый flow:

1. Проверить, что survey существует.
2. Проверить, что survey не закрыт.
3. Проверить, что segment существует.
4. Создать `SurveySend`.
5. Выбрать пользователей по JSON segment.
6. Для каждого пользователя:
   - найти активный invitation на этот survey;
   - если активный invitation есть — отозвать его;
   - сгенерировать новый raw token;
   - посчитать `token_hash`;
   - создать новый `Invitation`;
   - создать `InvitationDeliveryJob`;
   - сформировать public link `/s/{survey_id}/{token}`.
7. Закоммитить данные в PostgreSQL.
8. Поставить delivery jobs в Redis/RQ queue.

---

## Resend / reissue

Resend реализован через стратегию:

```text
revoke old active invitation -> create new invitation
```

Активный invitation ищется по условиям:

```text
survey_id = current survey
user_id = current user
revoked_at IS NULL
used_at IS NULL
```

Если такой invitation найден, он обновляется:

```text
revoked_at = now
status = "revoked"
resend_count = resend_count + 1
```

После этого создаётся новый invitation с новым token.

Важно:

старый raw token после revoke больше невалиден.

---

## GET /s/{survey_id}/{token}

Endpoint открывает public invite link.

Flow:

1. Получить raw token из URL.
2. Посчитать `token_hash`.
3. Найти invitation по:
   - `survey_id`;
   - `token_hash`.
4. Проверить состояние invitation:
   - invitation существует;
   - не revoked;
   - не used;
   - не expired.
5. Если invitation.status == `"sent"`, обновить статус на `"opened"`.
6. Вернуть статус invitation.

Response example:

```json
{
  "survey_id": 1,
  "invitation_id": 10,
  "status": "opened"
}
```

---

## GET errors

Текущая реализация:

| Case | Status |
|---|---:|
| Invitation not found | `404` |
| Invitation revoked | `409` |
| Invitation already used | `409` |
| Invitation expired | `409` |

Важно:

В текущем MVP `GET` после completion не возвращает страницу “спасибо”.  
Такой request считается `already used` и возвращает `409`.

Если нужен более дружелюбный UX, можно в будущем изменить `GET` после completion так, чтобы он возвращал thank-you state.

---

## POST /s/{survey_id}/{token}

Endpoint отправляет ответы пользователя.

Request example:

```json
{
  "answers": {
    "q1": "Да",
    "q2": 5
  }
}
```

Flow:

1. Получить raw token из URL.
2. Посчитать `token_hash`.
3. Найти invitation по:
   - `survey_id`;
   - `token_hash`.
4. Проверить состояние invitation:
   - invitation существует;
   - не revoked;
   - не used;
   - не expired.
5. Создать `Response`.
6. Сохранить `answers`.
7. Обновить invitation:
   - `used_at = now`;
   - `status = "completed"`.
8. Вернуть `response_id`.

Response example:

```json
{
  "ok": true,
  "response_id": 1
}
```

---

## POST errors

Текущая реализация:

| Case | Status |
|---|---:|
| Invitation not found | `404` |
| Invitation revoked | `409` |
| Invitation already used | `409` |
| Invitation expired | `409` |
| Empty or invalid `answers` | `422` |

---

## Completion

Completion фиксируется двумя действиями:

```text
INSERT INTO responses
UPDATE invitations SET used_at = now, status = "completed"
```

В таблице `responses` действует constraint:

```sql
UNIQUE (invitation_id)
```

Это означает:

```text
один invitation может породить только один response
```

---

## Повторное использование token

После successful submit:

```text
invitation.used_at IS NOT NULL
invitation.status = "completed"
```

Повторный `POST` с тем же token вернёт:

```text
409 Conflict
```

Повторный `GET` с тем же token тоже вернёт:

```text
409 Conflict
```

---

## Статусы invitation в token flow

Основные статусы:

```text
queued
sent
opened
completed
revoked
```

Типичный flow:

```text
queued -> sent -> opened -> completed
```

При resend/reissue:

```text
sent/opened/queued -> revoked
```

Expired сейчас не обязательно хранить как отдельный persisted status.

Лучше считать expired как derived state:

```text
expires_at <= now
AND used_at IS NULL
AND revoked_at IS NULL
```

---

## Promo codes

Promo codes не входят в текущий MVP.

В актуальной схеме и flow нет:

```text
promo_code_pool
promo_issuances
promo_code_status
reserved/issued promo logic
```

Поэтому текущий POST submit не выдаёт promo code.

---

## Future: Promo Flow

Если promo codes вернутся в roadmap, их лучше описать отдельным документом или отдельным разделом `Future Extension`.

Возможная будущая модель:

```text
promo_code_pool
promo_issuances
```

Возможные статусы promo code:

```text
available
reserved
issued
```

Возможный concurrent issuance flow:

```sql
SELECT *
FROM promo_code_pool
WHERE survey_id = :survey_id
  AND status = 'available'
FOR UPDATE SKIP LOCKED
LIMIT 1;
```

Затем в той же транзакции:

```text
UPDATE promo_code_pool SET status = 'issued'
INSERT promo_issuances
```

Но это не текущий MVP.

---

## Current End-to-End Flow

### Send

```text
create SurveySend
select users by Segment
revoke old active invitations
create new Invitations
generate raw tokens
store token_hash
create InvitationDeliveryJobs
enqueue jobs to Redis/RQ
```

### Open

```text
GET /s/{survey_id}/{token}
hash token
find invitation
validate state
mark opened if current status is sent
return invitation status
```

### Submit

```text
POST /s/{survey_id}/{token}
hash token
find invitation
validate state
insert Response
mark invitation as completed
return response_id
```

---

## Production notes

Перед production стоит улучшить token/public flow:

1. Сделать submit атомарным через transaction locking.
2. Обработать race condition между двумя параллельными POST.
3. Добавить rate limiting на public endpoints.
4. Рассмотреть `410 Gone` для expired invitations.
5. Сделать idempotent/friendly GET после completion.
6. Добавить schema validation для `answers`.
7. Не возвращать raw invite links из bulk send API в production.