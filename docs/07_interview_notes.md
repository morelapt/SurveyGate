# Interview Notes

This document is a personal interview preparation guide for explaining SurveyGate.

SurveyGate should be presented as a backend MVP, not as a production-ready commercial product.

## 1. Short Project Pitch

SurveyGate is a backend MVP for targeted UX research recruitment.

It allows an operator to create surveys, define user segments with JSON filters, generate tokenized survey invitations, queue delivery jobs and collect responses through public invite links.

The project demonstrates:

- FastAPI;
- async SQLAlchemy 2.0;
- PostgreSQL;
- Alembic migrations;
- JSON-based segmentation;
- secure invitation token hashing;
- public tokenized links;
- Redis/RQ-based delivery queue;
- tests and linting quality gate.

## 2. 60-Second Version

SurveyGate is a backend MVP for recruiting UX research participants.

The problem is that researchers often manually filter users, send links and track responses through spreadsheets, forms and chats. I built an API that stores user profiles, allows an operator to create surveys and JSON-based segments, generates one-time invitation links and accepts survey responses through public tokenized URLs.

One important design choice is that raw invitation tokens are not stored in the database. The system stores only a hash of the token, so a database leak would not immediately expose valid invite links.

Another important decision is separating `Invitation` from `InvitationDeliveryJob`. `Invitation` is the business entity that gives a user access to a survey. `InvitationDeliveryJob` is the technical delivery task that can later be retried, failed or processed by a worker.

Right now this is an MVP: message delivery is represented by a stub and Redis/RQ infrastructure. I also documented what would be required before production: real Telegram integration, retries, idempotency, rate limiting, observability, proper auth and personal data handling.

## 3. 3-Minute Version

SurveyGate is a backend MVP for automating UX research participant recruitment.

The core flow is:

```text
user registers
-> user profile is updated
-> operator creates survey
-> operator creates segment
-> system previews matching users
-> operator sends invitations
-> system creates tokenized invite links
-> delivery jobs are queued
-> user opens public invite
-> user submits response
```

The project is built with FastAPI, async SQLAlchemy 2.0, PostgreSQL, Alembic, Redis/RQ, pytest and ruff.

The most interesting part is segmentation. Segments are stored as JSON trees. For example, an operator can define a segment like "city is Moscow AND age is between 18 and 35". Before execution, this JSON is validated. Then it is compiled into a SQLAlchemy query. This gives flexibility for an MVP without building a full visual query builder or a normalized rules engine.

Another important part is invitation security. When an invitation is created, the system generates a random token and returns a public link. But the raw token is not stored in the database. Instead, the application stores a token hash. When the user opens the public link, the token is hashed again and matched against the database.

For delivery, I separated the business concept of an invitation from the technical concept of a delivery job. This lets the system evolve toward retries, backoff, failed jobs and worker recovery without changing the core invitation model.

I do not present this as production-ready. It is a backend MVP. Before real production usage, I would add proper operator authentication, bot endpoint protection, audit logs, rate limiting, real Telegram delivery, retry/backoff, outbox or sweeper logic, observability, privacy controls and stronger tests for failure scenarios.

## 4. Architecture Overview

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

The API layer is implemented with routers.

Business logic is placed in services.

Database models are represented with SQLAlchemy ORM.

Migrations are managed by Alembic.

## 5. Main Domain Entities

### User

A participant who can be invited to surveys.

### Segment

A reusable filter that defines which users should be targeted.

Segments are stored as JSON.

### Survey

A research activity that users can be invited to.

### SurveySend

A specific launch of a survey to a selected segment.

### Invitation

A business entity that gives a user access to a survey through a tokenized public link.

### InvitationDeliveryJob

A technical entity representing an attempt to deliver an invitation message.

### Response

A submitted answer payload for a survey invitation.

## 6. Why JSON-Based Segmentation?

I chose JSON-based segmentation because it is a pragmatic MVP solution.

Benefits:

- flexible structure;
- fast to implement;
- easy to send through API;
- supports nested AND/OR logic;
- easy to validate before execution;
- can be compiled into SQLAlchemy queries.

Trade-offs:

- harder to optimize than normalized rule tables;
- requires strict validation;
- harder to analyze with SQL directly;
- can become complex if the segment language grows too much.

Alternative designs:

- normalized segment rules table;
- custom query builder;
- SQL views/materialized views;
- search/indexing engine;
- external analytics/CDP tool.

For this project, JSON is a good MVP compromise because the main goal is to demonstrate backend logic and flexible targeting.

## 7. How Segment Processing Works

The flow is:

```text
operator sends JSON filters
-> validate_segment_tree checks structure and allowed fields/operators
-> compile_segment_query converts JSON into SQLAlchemy query
-> query is executed against users and related tables
```

The validator checks:

- allowed fields;
- allowed operators per field;
- correct group operators;
- basic value shape;
- nested rule structure.

The compiler turns the JSON tree into SQLAlchemy expressions.

This separates validation from query generation, which makes the code easier to reason about and test.

## 8. Why Hash Invitation Tokens?

Invitation links work like bearer tokens: whoever has the link can access the public invite flow.

Storing raw tokens in the database would be risky. If the database leaked, valid invite links would leak too.

So the system:

```text
generates random raw token
-> returns raw token only in invite link
-> stores token hash in database
-> hashes incoming token
-> compares hash with stored value
```

This is similar in spirit to storing password hashes instead of raw passwords, although the exact threat model is different.

## 9. Why Separate Invitation and DeliveryJob?

Because they answer different questions.

`Invitation` answers:

```text
Does this user have access to this survey?
Is the invite active, revoked, expired or completed?
```

`InvitationDeliveryJob` answers:

```text
Was a message delivery task created?
Was it queued?
Was it processed?
Did it fail?
Should it be retried?
```

This separation is useful because delivery is unreliable by nature. Telegram, Redis, the network or a worker can fail.

The business state should not be tightly coupled to one delivery attempt.

## 10. Why Redis/RQ?

Redis/RQ is used to move message delivery outside the request/response cycle.

Without a queue:

```text
operator sends invitations
-> API tries to send all messages synchronously
-> request can become slow
-> external delivery failures directly affect API response
```

With a queue:

```text
operator sends invitations
-> API creates invitations and delivery jobs
-> jobs are queued
-> worker processes delivery asynchronously
```

For an MVP, RQ is simpler than Celery.

Trade-offs:

- simpler setup;
- easier to explain;
- enough for a portfolio project;
- less feature-rich than Celery;
- needs extra reliability mechanisms for production.

## 11. What Does `queued` Mean?

`queued` means that the invitation has been created and the delivery job has been queued, but the worker has not yet marked the invitation as successfully delivered.

In the MVP demo, the public invite link is returned directly by the API, so it can be opened even while the invitation status is still `queued`.

Production interpretation:

```text
queued = created and waiting for delivery processing
sent = worker successfully delivered the message
opened = user opened the public link
completed = user submitted a response
```

In the current MVP, `queued` is acceptable for demo purposes because Telegram delivery is represented by stub logic.

## 12. Current Quality Gate

The current project quality gate is:

```bash
poetry run ruff check .
poetry run python -m pytest
```

Current state:

- ruff passes;
- tests pass;
- migration files are excluded from ruff because they are historical Alembic migration scripts.

## 13. What Is Not Production-Ready Yet?

This project is intentionally an MVP.

Not production-ready yet:

- operator API uses a shared `X-API-Key`;
- bot endpoints are not protected by Telegram webhook verification;
- Telegram delivery is not implemented yet;
- delivery uses stub logic;
- no retry/backoff/dead-letter mechanism;
- no outbox/sweeper recovery;
- no rate limiting;
- no audit log;
- no proper observability;
- no user deletion/retention policy;
- no production deployment setup.

## 14. Production Hardening Roadmap

Before a real launch, I would add:

### Security

- proper operator authentication;
- roles and permissions;
- audit logs;
- bot endpoint protection;
- rate limiting;
- protected Swagger/OpenAPI in production.

### Delivery Reliability

- real Telegram Bot API adapter;
- timeouts;
- retry with backoff;
- dead-letter handling;
- manual retry for failed jobs;
- worker service in production.

### Queue Reliability

- PostgreSQL as source of truth;
- pending job sweeper;
- stale processing job recovery;
- transactional outbox pattern or outbox-like flow.

### Idempotency

- idempotency key for bulk sends;
- protection from duplicate send requests;
- graceful handling of database integrity errors;
- atomic public invite submission.

### Observability

- structured logs;
- request/correlation IDs;
- queue metrics;
- worker heartbeat;
- alerts;
- error tracking.

### Data Protection

- consent;
- deletion;
- retention policy;
- restricted operator access;
- careful logging;
- secure backups.

## 15. Likely Interview Questions and Answers

### Why did you choose FastAPI?

Because it is a modern Python web framework with good async support, automatic OpenAPI generation, dependency injection and Pydantic integration. It is a good fit for an API-first backend MVP.

### Why async SQLAlchemy?

The project is API-centric and can involve I/O-bound operations: database access, Redis and later Telegram API calls. Async SQLAlchemy fits this model, though it adds complexity around sessions, lazy loading and tests.

### Why not Django?

Django would be a good option for a full admin-heavy product. But this project is API-first, lightweight and focused on FastAPI backend skills, so FastAPI is a better fit for my learning and interview goals.

### Why store segments as JSON?

Because for an MVP, JSON gives flexibility and allows nested filter logic without designing a complex rule table system too early. I compensate for this flexibility with explicit validation and controlled compilation to SQLAlchemy.

### Is JSON segmentation safe?

It can be safe if the system does not execute raw SQL from user input. In my case, JSON is validated against allowed fields and operators, then compiled into SQLAlchemy expressions. Raw arbitrary SQL is not accepted.

### Why hash invitation tokens?

Because invitation links are bearer secrets. If raw tokens were stored and the database leaked, valid invite links would leak too. Hashing reduces this risk.

### Why Redis/RQ?

To avoid doing message delivery synchronously inside the API request. The API creates jobs, and workers can process delivery independently.

### What happens if Redis is down?

In the MVP, enqueue failure is logged. For production, I would keep PostgreSQL as the source of truth and add a sweeper/requeue process that finds pending jobs and re-enqueues them later.

### What happens if a worker crashes?

In production, I would add retry logic, stale job recovery, heartbeat monitoring and dead-letter handling.

### Can the same token be submitted twice?

No. The response flow marks the invitation as used/completed, and repeated submission returns an error. There is also a database-level uniqueness constraint around responses per invitation.

### What are the main trade-offs in the project?

The main trade-offs are:

- JSON segmentation is flexible but harder to optimize;
- RQ is simple but less feature-rich than Celery;
- X-API-Key is enough for MVP but not production-grade auth;
- returning raw invite links is useful for local demo but should be restricted in production;
- storing answers as JSONB is flexible but needs survey schema validation before production.

## 16. Strong Points to Highlight

- not just CRUD;
- clear domain model;
- token hashing;
- JSON validation and compilation;
- async FastAPI + SQLAlchemy;
- Alembic migrations;
- Redis/RQ delivery pipeline;
- explicit MVP limitations;
- production readiness roadmap;
- tests and ruff quality gate;
- verified local demo scenario.

## 17. Weak Points to Be Honest About

- no real Telegram adapter yet;
- no UI;
- limited test coverage;
- shared API key instead of real auth;
- no retry/backoff yet;
- no production Dockerfile for API/worker yet;
- no observability stack;
- no full survey schema validation.

Good phrasing:

> I intentionally keep this project honest as a backend MVP. I can explain the current trade-offs and I have documented what needs to be added before production.

## 18. Personal Positioning

This project connects well with my previous UX research background.

I understand the product problem because I have worked with research processes and participant recruitment. At the same time, I use this project to demonstrate backend engineering skills: API design, data modeling, async database access, migrations, token security, queues and testing.

Good phrasing:

> My UX research background helps me understand the domain, but in this project I focus on backend implementation: data model, API flow, segmentation logic, invitation security and delivery architecture.