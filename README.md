# SurveyGate — UX Research Recruiting Platform (Backend MVP)

SurveyGate is a backend MVP for recruiting UX research participants via Telegram.

The project demonstrates an asynchronous API for user profiling, audience segmentation, and invitation management.

---

## 🚀 Problem

UX researchers often spend significant time on:

* finding participants
* manually filtering candidates
* sending invitations
* reusing the same respondents

Common tools:

* Google Forms + Excel
* Telegram chats
* manual outreach

These workflows do not scale and lack automation.

---

## 🎯 Solution (MVP Scope)

This project implements the backend layer of a recruiting platform:

* user profile storage
* segmentation based on flexible filters
* invitation management with tokens
* survey lifecycle handling

⚠️ This is a **backend MVP**:

* no UI
* no background workers
* no full Telegram bot integration

---

## 🏗 Architecture

```
FastAPI (async)
     ↓
PostgreSQL
     ↓
Alembic (migrations)
```

Key aspects:

* asynchronous API (FastAPI + SQLAlchemy 2.0)
* PostgreSQL as the primary database
* Alembic for schema migrations
* operator-oriented REST API

---

## ⚙ Tech Stack

* Python 3.12
* FastAPI
* SQLAlchemy 2.0 (async)
* PostgreSQL
* Alembic
* Docker Compose (local database)
* pytest

---

## 📦 Implemented Features

### Core domain

* Users (profiles)
* Surveys
* Segments (JSON-based filters)
* Invitations (token-based)

### Functionality

* create and store user profiles
* preview segment users
* send invitations
* resend invitations
* basic status handling

---

## 🗂 Domain Model

Main entities:

* User
* Survey
* Segment
* Invitation

Segments are defined as JSON conditions (AND / OR logic).

---

## 🔁 State Flows

**Survey**

```
draft → active → closed
```

**Invitation**

```
sent → opened → completed / expired / revoked
```

---

## 🔌 API Overview

### Operator API

* `POST /operator/surveys`
* `POST /operator/segments/preview`
* `POST /operator/surveys/{id}/send`
* `POST /operator/invitations/resend`

### Health

* `GET /health`

---

## 🧪 Tests

* async tests (pytest + pytest-asyncio)
* segmentation logic tests
* invitation flow tests

---

## 🚀 Quick Start

```bash
git clone https://github.com/morelapt/SurveyGate.git
cd SurveyGate

cp .env.example .env

docker compose up -d

poetry install

poetry run python -m alembic upgrade head

poetry run python -m uvicorn app.main:app --reload
```

Open:

```
http://127.0.0.1:8000/docs
```

---

## 📂 Project Structure

```
surveygate/
 ├── app/
 │   ├── api/
 │   ├── models/
 │   ├── services/
 │   ├── repositories/
 │   ├── core/
 │   └── main.py
 ├── migrations/
 ├── tests/
 ├── docs/
 ├── docker-compose.yml
 ├── .env.example
 └── README.md
```

---

## ⚖️ Design Decisions

**JSON-based segmentation**

* fast to implement for MVP
* harder to optimize at scale

**Async backend**

* better scalability
* more complex debugging

---

## 🛣 Future Work

* Telegram bot integration
* public invite flow (response endpoint)
* admin interface
* rate limiting
* background jobs

---

## 👤 Author

Backend & product design: Marat Magomedov
