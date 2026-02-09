SurveyGate — UX Research Recruiting Platform (MVP)

SurveyGate — это MVP-платформа для рекрутинга респондентов UX-исследований через Telegram: сбор профилей, сегментация аудитории и массовые приглашения без Excel-таблиц и хаотичных чатов.

🚀 Problem

UX-исследователи и продуктовые команды тратят много времени на:

поиск респондентов,
ручную фильтрацию,
рассылку приглашений,
повторный рекрутинг одних и тех же людей.

Часто используются:

Google Forms + Excel,
Telegram-чаты,
агентства (дорого),
ручные рассылки.

Боль: долго, не масштабируется, нет автоматизации сегментации и повторного использования базы.

🎯 Solution

SurveyGate предлагает:

Telegram-бот для респондентов,
Web-панель для исследователей,
конструктор сегментов,
invite-кампании,
выдачу промокодов,
аудит действий и GDPR-совместимое удаление.

🏗 Architecture

Telegram Bot
     ↓
FastAPI Backend
     ├── PostgreSQL
     ├── Redis / Queue Workers
     └── Admin / Researcher Panel


асинхронный backend,
очереди для массовых рассылок,
audit-лог,
rate-limiting.

⚙ Tech Stack

Python 3.12
FastAPI
SQLAlchemy (async)
PostgreSQL
Alembic
Redis + RQ / Celery
Docker / docker-compose
pytest
**Nginx (опционально)**

📦 MVP Features

Registration + consent capture
Profile storage
Segmentation filters
Invite campaigns
Promo codes
Survey completion tracking
/delete_me endpoint
Audit logs
Rate limiting
Roles: admin / researcher

🗂 Domain Model

Основные сущности:
User / Profile
Survey
Segment
Invitation
Response
PromoCode
AuditLog
ER-диаграмма и PRD находятся в /docs.

🔁 State Flows

Survey: draft → active → closed
Invitation: queued → sent → failed → responded
PromoCode: available → reserved → issued → expired
User: active → deleted

🔌 API Overview
Telegram Bot

POST /bot/register
POST /bot/consent
POST /bot/profile
GET /bot/surveys
POST /bot/respond
POST /bot/delete_me

Researcher Panel

POST /surveys
PATCH /surveys/{id}/status
POST /segments/preview
POST /surveys/{id}/send
GET /responses
GET /audit_logs

Admin

GET /users
DELETE /users/{id}
GET /metrics

🛣 Roadmap

v0 — Prototype
Bot + анкета
ручные фильтры
тестовая рассылка

MVP (v1)
сегменты
массовые инвайты
промокоды
audit-лог
роли
/delete_me

v1.5
UI сегментов
scheduling рассылок
dashboards

v2
billing
marketplace
ML-matching
public API

⚖️ Trade-offs

Telegram как канал
✅ быстрый рост базы
❌ зависимость от платформы

JSON-сегменты
✅ скорость MVP
❌ сложность оптимизации

Soft delete + anonymize
✅ соответствие регуляциям
❌ дополнительная логика

🧪 Tests
unit-тесты сервисов,
интеграционные тесты API,
фикстуры Postgres,
idempotency-кейсы рассылок.

🚀 How to run locally
git clone https://github.com/morelapt/SyrveyGate.git
cd SurveyGate
cp .env.example .env
docker-compose up --build
poetry run alembic upgrade head
poetry run uvicorn app.main:app --reload


После запуска:
API: http://localhost:8000/docs
Bot webhook: /bot/webhook

📂 Repository Structure
surveygate/
 ├── app/
 │   ├── api/
 │   ├── models/
 │   ├── services/
 │   ├── repositories/
 │   ├── workers/
 │   ├── core/
 │   └── main.py
 ├── migrations/
 ├── tests/
 ├── docs/
 │   ├── prd-lite.md
 │   ├── erd.png
 │   ├── architecture.png
 │   └── flows.md
 ├── docker-compose.yml
 ├── .env.example
 └── README.md

👤 Author

Backend & Product design: Marat Magomedov