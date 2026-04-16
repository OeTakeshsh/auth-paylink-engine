# 🔐💳 Headless Payment Link Engine + JWT Auth

**Production-ready backend combining secure JWT authentication (with multi-session support) and a headless Stripe payment link engine.**

Generate payment links in seconds, charge customers without a frontend, and get automatic updates via webhooks. Built as a scalable foundation for SaaS products, marketplaces, or any app that needs fast and secure billing.

---

## 🌐 Live Demo

- **Base URL**: https://auth-paylink-engine-production.up.railway.app/
- **Swagger UI**: https://auth-paylink-engine-production.up.railway.app/docs
- **ReDoc**: https://auth-paylink-engine-production.up.railway.app/redoc

> This deployment is for demonstration and portfolio purposes only.

---

## Local Dev (Requires Stripe Test Keys):

```bash
cp .env.example .env
docker-compose up
```
Make sure to add your Stripe & Postgres keys in .env

Use Stripe CLI to forward webhooks:
 
stripe listen --forward-to localhost:8000/webhooks/stripe

## Key Features

- JWT Authentication (access + refresh tokens)
- Multi-session support (multiple devices at the same time)
- Secure refresh token storage (SHA256 hashed — never plain text)
- Token revocation per session + remote logout
- **Headless Stripe Payment Link Engine**
- Automatic payment status updates via Stripe Webhooks
- Fully async FastAPI architecture
- Dockerized for production
- PostgreSQL + Redis + Celery background tasks
- Production-ready logging with Correlation IDs

---

## Payment Link Engine (Headless Billing)

A Stripe-powered system that lets you create and manage payment links without building your own checkout page.

### How it works

1. Create a payment link via the API  
2. Share the public link `/pay/{public_id}` with your customer  
3. Customer completes payment on **Stripe Checkout**  
4. Stripe sends a webhook → payment status is automatically updated in your database

---

## Payment Link Endpoints

| Method | Endpoint              | Auth | Description                          |
|--------|-----------------------|------|--------------------------------------|
| POST   | `/payment-links/`     | ✅   | Create a new payment link            |
| GET    | `/payment-links/`     | ✅   | List all payment links               |
| GET    | `/pay/{public_id}`    | ❌   | Public checkout page (no auth)       |
| POST   | `/webhooks/stripe`    | ❌   | Stripe webhook handler               |

---

## Tech Stack

**Backend**  
- Python 3.14 + FastAPI (async)  
- SQLAlchemy 2.0  

**Database**  
- PostgreSQL (asyncpg)  
- Redis  

**Authentication**  
- JWT (python-jose) + bcrypt  

**Payments**  
- Stripe SDK  

**DevOps**  
- Docker + Docker Compose  
- Poetry  
- Alembic migrations  
- pytest  

---

## API Overview

### Authentication

| Method | Endpoint           | Description              |
|--------|--------------------|--------------------------|
| POST   | `/users/`          | Register                 |
| POST   | `/users/login`     | Login                    |
| POST   | `/users/refresh`   | Refresh token            |
| POST   | `/users/logout`    | Logout                   |
| GET    | `/users/me`        | Current user             |

### Sessions

| Method | Endpoint                    | Description                     |
|--------|-----------------------------|---------------------------------|
| GET    | `/users/sessions`           | List active sessions            |
| DELETE | `/users/sessions/{id}`      | Revoke specific session         |

### System

| Method | Endpoint   | Description     |
|--------|------------|-----------------|
| GET    | `/health`  | Health check    |

---

## Security

- Refresh tokens stored as SHA256 hashes (never plain text)  
- Unique `jti` (UUID) for every token  
- Full multi-session support  
- Per-session token revocation  
- Strict validation (type + expiration)  
- Correlation ID logging for full request tracing  

---
## Author
Backend developer specialized in building secure, scalable, and production-ready APIs with Python and FastAPI.
