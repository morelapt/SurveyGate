# Token & Promo Flow

---

## Что такое token

Одноразовый секрет, связанный с invitation.

Хранится:
- token_hash
- expires_at
- used_at
- revoked_at

---

## TTL

expires_at = sent_at + ttl_days

GET/POST после expiry → 410 Gone

---

## Completion

POST:
- проверка token
- INSERT responses
- UPDATE invitations.used_at + status=completed

---

## Повторный клик

GET после completion → спасибо  
POST → 409

---

## Resend

- ищем активный invite
- revoked_at старого
- создаём новый

---

## Promo Pool

promo_code_pool:
- available
- reserved
- issued

promo_issuances:
- кто получил

---

## Конкурентная выдача

В транзакции:

- SELECT ... FROM promo_code_pool
  WHERE status='available'
  FOR UPDATE SKIP LOCKED
- UPDATE status='issued'
- INSERT promo_issuances

---

## Поток

Send:
- create invitations
- generate token
- store hash

GET:
- validate token
- mark opened

POST:
- validate
- save responses
- issue promo
