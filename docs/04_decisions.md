# Architectural Decisions (ADR)

---

## ADR-001: Split users and user_identities

PII (telegram_id) вынесен отдельно, чтобы:
- реализовать /delete_me
- сохранить аналитику
- не терять историю

---

## ADR-002: token_hash instead of raw token

Если БД утекла — по hash нельзя пройти опрос.

---

## ADR-003: Partial unique on active invitations

История сохраняется, но активный всегда один.

---

## ADR-004: Promo pool + issuance

Промокоды загружаются заранее.
Факт выдачи фиксируется отдельно.

Позволяет:
- конкуренцию
- аудит
- строгие инварианты

---

## ADR-005: Enum for statuses

Закрытые наборы:
- invitation_status
- promo_code_status
- survey_status

Если появятся workflow-статусы → lookup-таблицы.
