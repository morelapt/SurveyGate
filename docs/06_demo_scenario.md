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
-> try to submit the same token again
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
  "user_ids": [1]
}
```

If the local database is not empty, IDs may differ and the response may contain more than one matching user:

```json
{
  "segment_id": 2,
  "user_ids": [1, 2]
}
```

The key point is that users matching the JSON segment filter are returned.

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
  "invitation_id": 1,
  "status": "queued"
}
```

In this MVP, the public link can be opened directly from the API response for demo purposes.

The `queued` status means that the invitation has been created 
and a delivery job has been queued, but the worker has not yet marked the invitation 
as successfully delivered.

In a production flow, a user would normally receive the link only after the delivery worker 
sends the message through Telegram.

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
  "response_id": 1
}
```

After successful submission:

- response is stored in PostgreSQL;
- invitation is marked as completed/used;
- the same token cannot be submitted again.

## 9. Try to submit the same token again

```bash
curl -X POST "http://127.0.0.1:8000/s/1/<token>" \
  -H "Content-Type: application/json" \
  -d '{
    "answers": {
      "q1": "Second attempt",
      "q2": 1
    }
  }'
```

Expected result:

```json
{
  "detail": "Invitation already used"
}
```

This confirms that the public invite token is single-use.

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
- single-use public invite token protection;
- separation between `Invitation` and `InvitationDeliveryJob`;
- Redis/RQ-ready delivery architecture.

## Interview Talking Points

During an interview, this demo can be explained as:

> I start with a user who registers through a bot-like API. 
> Then I create a survey and a reusable JSON segment. 
> The segment is validated and compiled into a SQLAlchemy query. 
> When I send invitations, the system creates tokenized invite links, 
> stores only token hashes, revokes previous active invitations if needed 
> and creates delivery jobs. 
> The public endpoint then allows the user to open the invite and submit a response. 
> Message delivery is currently represented by a stub and Redis/RQ queue infrastructure, 
> while the production roadmap describes how I would add real Telegram delivery, retries, 
> idempotency and observability.