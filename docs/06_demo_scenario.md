# Demo Scenario

This document describes a minimal local scenario for demonstrating SurveyGate during an interview.

The goal is to show the main backend flow:

```text
register user
-> create survey
-> create segment
-> preview segment
-> send invitations
-> create delivery job
-> open public invite
-> submit response
```

## Prerequisites

Start from a clean local environment.

```bash
cp .env.example .env
docker compose up -d
poetry install
poetry run python -m alembic upgrade head
poetry run python -m uvicorn app.main:app --reload
```

The API should be available at:

```text
http://127.0.0.1:8000
```

Swagger UI:

```text
http://127.0.0.1:8000/docs
```

## 1. Register a user

This endpoint simulates a Telegram bot registration flow.

```bash
curl -X POST "http://127.0.0.1:8000/bot/users/register" \
  -H "Content-Type: application/json" \
  -d '{
    "telegram_id": 100001,
    "telegram_username": "demo_user"
  }'
```

Expected result:

```json
{
  "user_id": 1,
  "is_new": true
}
```

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

Expected result:

```json
{
  "ok": true
}
```

## 3. Create a survey

```bash
curl -X POST "http://127.0.0.1:8000/operator/surveys" \
  -H "X-API-Key: dev-operator-key" \
  -H "Content-Type: application/json" \
  -d '{
    "title": "UX Interview Study",
    "status": "active"
  }'
```

Expected result:

```json
{
  "survey_id": 1
}
```

## 4. Create a segment

This segment targets users from Moscow aged 18-35.

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

Expected result:

```json
{
  "segment_id": 1
}
```

## 5. Preview segment

```bash
curl -X GET "http://127.0.0.1:8000/operator/segments/1/preview?limit=20" \
  -H "X-API-Key: dev-operator-key"
```

Expected result:

```json
{
  "segment_id": 1,
  "users": [
    {
      "user_id": 1,
      "city": "Moscow",
      "age": 25,
      "has_children": false
    }
  ]
}
```

The exact response shape may differ depending on the current response schema, but the key point is that the registered user should match the segment.

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

Expected result:

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

Important:

- the raw token is returned only for local demo purposes;
- the database stores only a token hash;
- invitation status should be `queued`;
- a delivery job should be created for the invitation.

## 7. Open public invite

Take the `invite_link` from the previous response.

Example:

```bash
curl -X GET "http://127.0.0.1:8000/s/1/<token>"
```

Expected result:

```json
{
  "survey_id": 1,
  "status": "opened"
}
```

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

Expected result:

```json
{
  "ok": true,
  "response_id": 1,
  "invitation_id": 1
}
```

After successful submission:

- response is stored in PostgreSQL;
- invitation is marked as completed;
- the same token cannot be submitted again.

## What This Demo Shows

This scenario demonstrates:

- async FastAPI endpoints;
- user registration and profile update;
- JSON-based segmentation;
- segment validation and SQL compilation;
- operator API protection with `X-API-Key`;
- one-time invitation token flow;
- token hashing;
- public invite open/submit flow;
- separation between `Invitation` and `InvitationDeliveryJob`;
- Redis/RQ-ready delivery architecture.

## Interview Talking Points

During an interview, this demo can be explained as:

> I start with a user who registers through a bot-like API. 
> Then I create a survey and a reusable JSON segment. 
> The segment is validated and compiled into a SQLAlchemy query. 
> When I send invitations, the system creates tokenized invite links, stores only token hashes, revokes previous active invitations if needed and creates delivery jobs. 
> The public endpoint then allows the user to open the invite and submit a response. 
> Message delivery is currently represented by a stub and Redis/RQ queue infrastructure, while the production roadmap describes how I would add real Telegram delivery, retries, idempotency and observability.