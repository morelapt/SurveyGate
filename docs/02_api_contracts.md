# API Contracts

Документ описывает только контракты API (без реализации).

---

## Bot-side

### POST /bot/users/register

Создать пользователя по telegram_id.

Request:
{
  "telegram_id": 123456,
  "language": "ru",
  "source": "tg_bot"
}

Response:
{
  "user_id": "uuid",
  "is_new": true
}

---

### PATCH /bot/users/profile

Обновление анкеты.

Request:
{
  "telegram_id": 123,
  "age": 33,
  "city": "Москва",
  "devices": ["tv"],
  "services": ["ivi"]
}

---

### POST /bot/users/delete_me

Soft-delete + отзыв активных инвайтов.

---

## Operator-side

### POST /operator/surveys
Создание survey.

---

### POST /operator/segments
Создание сегмента (jsonb filters).

---

### POST /operator/surveys/{id}/send_invitations

Создание/обновление инвайтов.

Response:
{
  "send_id": "uuid",
  "users_targeted": 400,
  "invitations_created": 350,
  "invitations_resend": 50
}

---

### GET /operator/surveys/{id}/stats

Метрики:
- invited
- opened
- completed
- promo_issued
- conversion_completed

---

## Public

### GET /s/{survey_id}/{token}

200 — ok  
410 — expired  
404 — revoked / not found  
409 — already used  

---

### POST /s/{survey_id}/{token}

Submit answers + promo code.

Errors:
- 410 expired
- 404 revoked
- 409 used
- 400 invalid payload
