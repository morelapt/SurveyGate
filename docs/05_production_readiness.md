# Production Readiness Roadmap

SurveyGate is currently a backend MVP designed for interview demonstration and architectural discussion.

It is not yet ready for commercial production usage.

This document describes what should be added before a real production launch.

## 1. API Security

Current MVP state:

- operator API is protected with a single `X-API-Key`;
- bot-like endpoints accept user data directly;
- public invite endpoints are accessible through bearer-style links.

Production improvements:

- replace shared `X-API-Key` with proper operator authentication;
- add roles and permissions for operator actions;
- protect bot endpoints with a service token or Telegram webhook verification;
- add audit logging for operator actions;
- add rate limiting for operator, bot and public endpoints;
- configure CORS, TrustedHost and security headers;
- disable or protect Swagger/OpenAPI in production.

Why it matters:

The project is API-centric. Authentication, authorization and resource control are critical risks for this type of system.

## 2. Secrets and Sensitive Data

Current MVP state:

- invite links are returned by the send invitations endpoint for demo purposes;
- local configuration uses `.env`;
- message delivery is represented by stub logging.

Production improvements:

- never log `DATABASE_URL` or other secrets;
- never log raw invitation tokens;
- avoid logging full message text if it may contain personal data;
- mask or hash `telegram_id` in logs where possible;
- use deployment-level secret management;
- separate dev and prod settings;
- avoid returning invite links from bulk APIs unless strictly required.

Why it matters:

Invitation links are bearer secrets. Anyone with the link can access the public invite flow.

## 3. Reliable Message Delivery

Current MVP state:

- `InvitationDeliveryJob` exists;
- Redis/RQ queue integration exists;
- actual Telegram delivery is still a stub.

Production improvements:

- implement a real Telegram Bot API adapter;
- add request timeouts;
- handle Telegram `429 Too Many Requests`;
- add retry with backoff;
- add delivery rate limits;
- add failed/dead-letter handling;
- add manual retry for failed jobs;
- run worker as a separate production service.

Why it matters:

The most important production risk is not creating invitations, but reliably delivering them.

## 4. Queue Reliability

Current MVP state:

- delivery jobs are created in PostgreSQL;
- after commit they are enqueued into Redis/RQ.

Potential problem:

- database commit can succeed;
- Redis enqueue can fail;
- then a delivery job exists in PostgreSQL but is missing from the queue.

Production improvements:

- treat PostgreSQL as the source of truth;
- add a sweeper/requeue process for pending jobs;
- requeue stale queued/processing jobs;
- consider a transactional outbox pattern;
- track queue health metrics.

Why it matters:

Redis should be treated as a transport layer, not as the only source of truth.

## 5. Idempotency and Race Conditions

Production risks:

- operator clicks "send" twice;
- HTTP request is retried after timeout;
- two workers process the same job;
- two public submissions happen at the same time;
- invitation is revoked while delivery is already queued.

Production improvements:

- add `Idempotency-Key` for bulk send operations;
- prevent duplicate sends without explicit confirmation;
- handle database `IntegrityError` gracefully;
- use atomic status transitions for delivery jobs;
- use atomic public invite submission;
- enforce unique constraints at the database level;
- return correct conflict responses instead of generic 500 errors.

## 6. Public Form Validation

Current MVP state:

- public answers are stored as JSON.

Production improvements:

- define a survey question schema;
- validate answers against the schema;
- limit request body size;
- rate-limit public endpoints;
- protect against repeated submission;
- avoid leaking invite tokens through logs or referrers.

Why it matters:

Flexible JSON is useful for MVP speed, but production data needs validation and limits.

## 7. Deployment

Current MVP state:

- Docker Compose starts PostgreSQL and Redis;
- API is run locally with Uvicorn;
- no production API/worker containers yet.

Production improvements:

- add Dockerfile;
- add API container;
- add worker container;
- add migration job;
- run without `--reload`;
- keep PostgreSQL and Redis private;
- add reverse proxy;
- enable HTTPS;
- add healthchecks;
- define backup/restore process;
- document rollback strategy.

## 8. Observability

Current MVP state:

- `/health` and `/health/db` exist.

Production improvements:

- add `/health/live`;
- add `/health/ready`;
- add Redis health check;
- add worker heartbeat;
- add structured logs;
- add request/correlation IDs;
- collect API latency and error metrics;
- collect queue metrics: pending, queued, processing, sent, failed;
- add alerts for failed jobs, growing queues and dead workers;
- integrate error tracking such as Sentry.

Why it matters:

For this project, a healthy API is not enough. The system must also prove that invitations are actually being delivered.

## 9. Personal Data and Privacy

The project stores user profile data, Telegram identifiers and survey responses.

Production improvements:

- add privacy policy;
- collect consent for participation and data processing;
- implement user deletion;
- implement data retention policy;
- restrict operator access to personal data;
- audit access and modifications;
- protect backups;
- minimize stored data.

## 10. Production-Grade Tests and CI

Current MVP state:

- tests cover some core flows.

Production improvements:

- test full flow: register user -> create survey -> create segment -> send invitations -> process delivery -> submit response;
- test expired/revoked/used invitations;
- test duplicate public submission;
- test duplicate send;
- test Redis/Telegram failure scenarios;
- test retry and failed jobs;
- test auth negative cases;
- test migrations on a clean database;
- add CI for ruff, pytest, migration smoke test and Docker build.

## Summary

The MVP is useful for demonstrating backend design, but production readiness requires a hardening layer:

- security;
- reliable delivery;
- queue recovery;
- idempotency;
- validation;
- deployment;
- observability;
- privacy;
- tests.

The next engineering step should not be adding more business features. It should be making the existing flow reliable, observable and safe.