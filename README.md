# SurveyGate — UX Research Recruiting Platform Backend MVP

SurveyGate is a backend MVP for recruiting UX research participants through targeted survey invitations.

The project demonstrates an asynchronous FastAPI backend with:

- user profile storage;
- JSON-based audience segmentation;
- survey and invitation management;
- hashed invitation tokens;
- public invite links;
- Redis/RQ-based delivery queue;
- PostgreSQL persistence and Alembic migrations.

## Problem

UX researchers often need to:

- find relevant participants;
- filter users by profile attributes;
- send survey or interview invitations;
- avoid repeatedly contacting the same respondent;
- track whether an invitation was opened or completed.

In many teams this is done through a mix of Google Forms, spreadsheets, Telegram chats and manual outreach. That workflow does not scale well and is difficult to audit.

## MVP Scope

This project implements the backend layer of a recruiting platform.

Implemented in the current MVP:

- user registration/profile endpoints for bot-like flows;
- operator API protected with `X-API-Key`;
- survey creation;
- segment creation with JSON filters;
- segment preview;
- invitation generation;
- invitation token hashing;
- public invite open/submit flow;
- delivery job creation;
- Redis/RQ queue integration for invitation delivery;
- PostgreSQL schema migrations with Alembic;
- automated tests for core flows.

Current limitations:

- no UI/admin panel;
- no real Telegram Bot API integration yet;
- message delivery is represented by a stub sender;
- no production-grade authentication/authorization;
- no rate limiting;
- no full observability stack;
- no production deployment configuration yet.

## Architecture

```text
Client / Operator
        |
        v
FastAPI application
        |
        +--> PostgreSQL
        |       - users
        |       - surveys
        |       - segments
        |       - survey sends
        |       - invitations
        |       - invitation delivery jobs
        |       - responses
        |
        +--> Redis / RQ
                - background delivery queue
                - worker processes delivery jobs
```

## Tech Stack

- Python 3.12
- FastAPI
- SQLAlchemy 2.0 async
- PostgreSQL
- Alembic
- Redis
- RQ
- Docker Compose
- pytest
- pytest-asyncio
- ruff

## Main Domain Concepts

### User

A participant who can be invited to surveys.

### Segment

A reusable JSON-based filter that describes which users should be targeted.

Example:

```json
{
  "op": "AND",
  "rules": [
    {"field": "city", "op": "EQ", "value": "Moscow"},
    {"field": "age", "op": "BETWEEN", "value": [18, 35]}
  ]
}
```

Segments are first validated and then compiled into a SQLAlchemy query.

### Survey

A research activity that users can be invited to.

### SurveySend

A specific launch of invitations for a survey and segment.

### Invitation

A business entity representing a user's right to open and submit a survey response through a tokenized public link.

The raw token is shown only when the invite is created. The database stores only a token hash.

### InvitationDeliveryJob

A technical entity representing a delivery attempt for an invitation.

This separation is intentional:

- `Invitation` answers: "Can this user access this survey?"
- `InvitationDeliveryJob` answers: "Was the message delivered to the user?"

## State Flows

### Survey

```text
draft -> active -> closed
```

### Invitation

```text
queued -> sent -> opened -> completed
            |
            +-> revoked
            +-> expired
```

### InvitationDeliveryJob

```text
pending -> queued -> processing -> sent
                                |
                                +-> failed
```

## API Overview

### Health

```http
GET /health
GET /health/db
```

### Bot-like User API

```http
POST /bot/users/register
GET /bot/users/profile
PATCH /bot/users/profile
```

### Operator API

All operator endpoints require:

```http
X-API-Key: <operator-api-key>
```

Available endpoints:

```http
GET /operator/ping
POST /operator/surveys
POST /operator/segments
GET /operator/segments/{segment_id}/preview
POST /operator/surveys/{survey_id}/send_invitations
```

### Public Invite API

```http
GET /s/{survey_id}/{token}
POST /s/{survey_id}/{token}
```

## Quick Start

### 1. Clone the repository

```bash
git clone https://github.com/morelapt/SurveyGate.git
cd SurveyGate
git checkout feature/redis-delivery-queue
```

### 2. Create local environment file

```bash
cp .env.example .env
```

Example local values:

```env
ENV=dev

POSTGRES_DB=surveygate
POSTGRES_USER=surveygate
POSTGRES_PASSWORD=surveygate
DATABASE_HOST=localhost
DATABASE_PORT=5432

DATABASE_URL=postgresql+asyncpg://surveygate:surveygate@localhost:5432/surveygate
DATABASE_URL_SYNC=postgresql+psycopg://surveygate:surveygate@localhost:5432/surveygate

REDIS_URL=redis://localhost:6379/0

OPERATOR_API_KEY=dev-operator-key
SECRET_KEY=dev-secret-key-change-me
```

### 3. Start infrastructure

```bash
docker compose up -d
```

### 4. Install dependencies

```bash
poetry install
```

### 5. Run migrations

```bash
poetry run python -m alembic upgrade head
```

### 6. Start API

```bash
poetry run python -m uvicorn app.main:app --reload
```

Open:

```text
http://127.0.0.1:8000/docs
```

## Running Tests

```bash
poetry run python -m pytest
```

Run linting:

```bash
poetry run ruff check .
```

## Example Flow

### 1. Create a survey

```bash
curl -X POST "http://127.0.0.1:8000/operator/surveys" \
  -H "X-API-Key: dev-operator-key" \
  -H "Content-Type: application/json" \
  -d '{
    "title": "UX Interview Study",
    "status": "draft"
  }'
```

### 2. Create a segment

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

### 3. Preview segment users

```bash
curl -X GET "http://127.0.0.1:8000/operator/segments/1/preview?limit=20" \
  -H "X-API-Key: dev-operator-key"
```

### 4. Send invitations

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

The response includes generated invite links for local demo purposes.

In a production system, invite links are bearer secrets and should not be returned freely from a bulk API response.

## Project Structure

```text
surveygate/
├── app/
│   ├── core/
│   ├── db/
│   ├── models/
│   ├── queue/
│   ├── routers/
│   ├── schemas/
│   ├── scripts/
│   ├── services/
│   └── main.py
├── docs/
├── migrations/
├── tests/
├── docker-compose.yml
├── pyproject.toml
└── README.md
```

## Key Design Decisions

### JSON-based segmentation

Segments are stored as JSON trees.

Why this is useful for an MVP:

- fast to implement;
- flexible enough for different filters;
- easy to validate before execution;
- can be compiled into SQLAlchemy queries.

Trade-offs:

- harder to optimize than fully normalized rule tables;
- requires careful validation;
- more complex analytics on segment structure.

### Hashed invitation tokens

Raw invitation tokens are not stored in the database.

Instead:

1. a random token is generated;
2. the token is shown in the public invite link;
3. only a hash of the token is stored;
4. incoming public requests hash the provided token and compare it with the stored hash.

This reduces the damage of a database leak.

### Invitation vs DeliveryJob

The project separates business state from delivery mechanics.

`Invitation` is the business object.

`InvitationDeliveryJob` is the technical delivery task.

This allows the system to evolve toward retries, backoff, failed jobs and worker recovery without changing the core invitation model.

### Redis/RQ queue

Redis/RQ is used to move message delivery outside the request/response cycle.

The current implementation is intentionally MVP-level:

- delivery jobs are stored in PostgreSQL;
- jobs are enqueued into Redis/RQ;
- actual Telegram sending is still represented by a stub.

For production, PostgreSQL should remain the source of truth and Redis should be treated as a delivery transport.

## Production Readiness

SurveyGate is intentionally a backend MVP, not a production-ready commercial product.

Before a real launch, the most important improvements would be:

- production-grade authentication and authorization;
- protection for bot-facing endpoints;
- audit log for operator actions;
- rate limiting;
- real Telegram Bot API integration;
- retry/backoff/dead-letter logic for failed delivery jobs;
- outbox or sweeper process for queue reliability;
- idempotency keys for bulk sends;
- atomic handling of public invite submission;
- validation of survey answers against a survey schema;
- Dockerfile and separate API/worker containers;
- HTTPS and reverse proxy configuration;
- readiness/liveness checks;
- worker heartbeat;
- metrics and alerts for queue health;
- careful handling of personal data;
- user deletion and retention policy;
- CI pipeline for linting, tests and migration checks.

More details are described in `docs/05_production_readiness.md`.

## Interview Positioning

This project is best presented as:

> A backend MVP for targeted UX research recruitment. It demonstrates async FastAPI development, SQLAlchemy 2.0, PostgreSQL schema design, JSON-based segmentation, secure invitation tokens, public invite flow and Redis/RQ-based delivery queue. The project is not production-ready yet, but the main production gaps are documented and understood.

## Author

Marat Magomedov