<div align="center">

# 💰 BudgetBot

**AI-Powered Personal Finance Manager**

Automatically classify transactions, track spending against budgets, and get personalized financial insights — powered by a hybrid AI engine (rule-based + LLM).

[![Python 3.12](https://img.shields.io/badge/Python-3.12-blue?logo=python&logoColor=white)](https://python.org)
[![React 19](https://img.shields.io/badge/React-19-61DAFB?logo=react&logoColor=black)](https://react.dev)
[![FastAPI](https://img.shields.io/badge/FastAPI-009688?logo=fastapi&logoColor=white)](https://fastapi.tiangolo.com)
[![AWS](https://img.shields.io/badge/AWS-Cloud-orange?logo=amazonwebservices&logoColor=white)](https://aws.amazon.com)
[![License: MIT](https://img.shields.io/badge/License-MIT-green.svg)](LICENSE)

</div>

---

## Table of Contents

- [Overview](#overview)
- [Key Features](#key-features)
- [Architecture](#architecture)
- [Tech Stack](#tech-stack)
- [Project Structure](#project-structure)
- [Getting Started](#getting-started)
  - [Prerequisites](#prerequisites)
  - [Local Development](#local-development)
  - [Frontend Development](#frontend-development)
  - [Running Tests](#running-tests)
- [Configuration](#configuration)
- [API Reference](#api-reference)
- [AI Classification Pipeline](#ai-classification-pipeline)
- [Deployment](#deployment)
- [Evaluation](#evaluation)
- [Contributing](#contributing)
- [License](#license)

---

## Overview

BudgetBot is a full-stack web application that helps users manage personal finances through **AI-powered transaction classification**, **budget tracking**, and an **interactive money coach chatbot**.

Upload a bank statement (CSV or PDF), and BudgetBot will:

1. **Parse** the file and extract transactions
2. **Classify** each transaction into categories using a hybrid AI pipeline
3. **Visualize** spending patterns with interactive charts
4. **Track** budgets and alert when limits are exceeded
5. **Answer** financial questions via a streaming AI chatbot

The application runs **fully locally** with zero cloud dependencies (SQLite + rule-based AI). Flipping environment variables switches it to production AWS services (Amazon Bedrock, S3, RDS, SQS).

---

## Key Features

| Feature | Description |
|---------|-------------|
| 🤖 **Hybrid AI Classification** | Keyword rules handle clear cases; LLM (Amazon Bedrock) handles ambiguous ones; local fallback if cloud fails |
| 📊 **Interactive Dashboard** | Donut charts, bar charts, category breakdowns, and monthly comparisons |
| 💬 **AI Money Coach** | Streaming chatbot (SSE) with server-side memory, tool calling (`set_budget`), and domain guardrails |
| 📁 **Multi-Format Upload** | CSV with configurable column mapping and PDF table extraction via `pdfplumber` |
| 🎯 **Budget Management** | Per-category spending limits with progress bars and exceeded alerts |
| 🧠 **Personalization** | User corrections become high-confidence training examples — personalization without fine-tuning |
| 🔐 **User Isolation** | Per-user data via JWT `sub` claim (Cognito) or `X-User-Id` header (dev) |
| 🇻🇳 **Bilingual UI** | Vietnamese primary interface with English category enums |
| 📈 **Observability** | 13 custom CloudWatch metrics covering the entire pipeline |
| 🚀 **CI/CD** | Single push to `main` deploys backend (Docker → ECR → Lambda) and frontend (Vite → S3 → CloudFront) |

---

## Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                         Frontend (React 19 + Vite)              │
│  ┌──────────┐  ┌───────────┐  ┌──────────┐  ┌───────────────┐  │
│  │ AuthPage │  │ Dashboard │  │  Upload   │  │   Chatbot     │  │
│  │ (Cognito)│  │ (Charts)  │  │ (CSV/PDF) │  │ (SSE Stream)  │  │
│  └────┬─────┘  └─────┬─────┘  └─────┬─────┘  └──────┬────────┘  │
│       │              │              │               │            │
└───────┼──────────────┼──────────────┼───────────────┼────────────┘
        │              │              │               │
        ▼              ▼              ▼               ▼
┌─────────────────────────────────────────────────────────────────┐
│                    Backend (FastAPI + Uvicorn)                   │
│  ┌──────────────────────────────────────────────────────────┐   │
│  │                    API Layer (app.py)                     │   │
│  │   /upload · /summary · /budgets · /chat · /transactions  │   │
│  └────────────────────────┬─────────────────────────────────┘   │
│                           │                                     │
│  ┌────────────────────────▼─────────────────────────────────┐   │
│  │              Business Logic (handlers.py)                 │   │
│  └──┬──────────────┬──────────────┬──────────────┬──────────┘   │
│     │              │              │              │               │
│     ▼              ▼              ▼              ▼               │
│  ┌──────┐   ┌──────────┐   ┌──────────┐   ┌──────────┐         │
│  │  AI  │   │ Storage  │   │UserStore │   │ Chatbot  │         │
│  │      │   │          │   │          │   │          │         │
│  │Rules │   │  Local   │   │  SQLite  │   │ Bedrock  │         │
│  │LLM   │   │  S3      │   │  Postgres│   │ Memory   │         │
│  │Local │   │          │   │  Dynamo  │   │ Tools    │         │
│  └──────┘   └──────────┘   └──────────┘   └──────────┘         │
└─────────────────────────────────────────────────────────────────┘
```

### Production AWS Architecture

```
CloudFront + WAF  →  API Gateway v2  →  Lambda (Docker/ECR)
                                         │
                    ┌────────────────────┼────────────────────┐
                    ▼                    ▼                    ▼
              Amazon S3           Amazon RDS             Amazon SQS
           (File Upload)      (PostgreSQL)           (Async Processing)
                    │
                    ▼
             Amazon Bedrock
          (Claude / Nova LLM)
```

---

## Tech Stack

### Backend

| Component | Technology | Purpose |
|-----------|-----------|---------|
| Framework | **FastAPI** (Python 3.12) | ASGI web framework with auto-generated OpenAPI docs |
| Server | **Uvicorn** | Local ASGI development server |
| AWS Adapter | **Mangum** | FastAPI → AWS Lambda handler |
| PDF Parsing | **pdfplumber** | Extract tables from bank statement PDFs |
| AWS SDK | **boto3** | Bedrock, S3, SQS, CloudWatch, Secrets Manager |

### Frontend

| Component | Technology | Purpose |
|-----------|-----------|---------|
| UI Framework | **React 19** | Component-based SPA |
| Build Tool | **Vite 8** | Fast HMR dev server + optimized production builds |
| Charts | **Recharts** | Bar charts (donut chart is custom SVG) |
| Markdown | **react-markdown** | Render chatbot markdown responses |
| Auth | **amazon-cognito-identity-js** | JWT-based authentication |

### Database (Pluggable)

| Backend | Use Case |
|---------|----------|
| **SQLite** | Local development (default) |
| **Amazon RDS PostgreSQL** | Production |
| **Amazon DynamoDB** | Serverless production |
| **Amazon DocumentDB / MongoDB Atlas** | Document-based storage |
| **RDS MySQL / Aurora MySQL** | MySQL-compatible production |

### AI / ML

| Component | Details |
|-----------|---------|
| LLM Provider | **Amazon Bedrock** (Converse API) |
| Models | `anthropic.claude-3-5-haiku` / `amazon.nova-2-lite-v1:0` |
| Strategy | Hybrid — rules first → LLM for ambiguous → local fallback |
| Chatbot | Streaming SSE with tool calling, memory summarization, domain guardrails |
| Prompt Personalization | User correction history injected as high-confidence examples |

### AWS Cloud Infrastructure

| Service | Technology | Role |
|---------|-----------|------|
| **Compute** | AWS Lambda | Serverless compute — runs FastAPI via Mangum handler from container image |
| **Container Registry** | Amazon ECR | Stores Docker images for Lambda deployment |
| **API Gateway** | Amazon API Gateway v2 (HTTP API) | Front door for all API requests with JWT Authorizer (Cognito) |
| **AI / ML** | Amazon Bedrock | LLM inference — Claude 3.5 Haiku & Amazon Nova for transaction classification and chatbot |
| **Storage** | Amazon S3 | Bank statement uploads (CSV/PDF) + frontend static website hosting |
| **Queue** | Amazon SQS + DLQ | Async file processing queue with dead-letter queue for failed messages |
| **Database** | Amazon RDS (PostgreSQL) | Production relational database for transactions, budgets, chat memory |
| **Database** | Amazon DynamoDB | Serverless NoSQL option for user data |
| **Database** | Amazon DocumentDB | MongoDB-compatible document database option |
| **CDN** | Amazon CloudFront | Global content delivery for frontend with cache invalidation on deploy |
| **WAF** | AWS WAF | Web application firewall attached to CloudFront (rate limiting, IP rules) |
| **Auth** | Amazon Cognito | User Pool for sign-up / sign-in / JWT token management |
| **DNS** | Amazon Route 53 | Custom domain routing with health checks |
| **TLS** | AWS Certificate Manager (ACM) | Free SSL/TLS certificates for custom domain |
| **Monitoring** | Amazon CloudWatch | 13 custom metrics, alarms, dashboards (namespace: `BudgetBot/W7`) |
| **Secrets** | AWS Secrets Manager | Auto-rotation and retrieval of database credentials |
| **Networking** | VPC + Private Subnets | Network isolation with VPC Interface Endpoints for S3, SQS, Bedrock, Secrets Manager |
| **IaC** | GitHub Actions | CI/CD pipeline — Docker build → ECR push → Lambda update → S3 sync → CloudFront invalidation |

---

## Project Structure

```
ai-fintech-budget-automation/
├── .github/
│   └── workflows/
│       └── deploy.yml                    # CI/CD: Docker build, Lambda deploy, S3 sync
│
├── assets/                               # Cost estimate images
├── recordings/                           # Course recording references
├── Slide/                                # Presentation slides (PDF)
├── W7_envidence/                         # Hackathon evidence pack
│   ├── W7_evidence_final.md              # Architecture & deployment evidence
│   ├── W7_AI_implementation_evidence.md  # AI implementation proof
│   └── image/                            # AWS console screenshots
│
└── starter_apps/
    └── budgetbot/                        # ← Main application
        ├── Dockerfile                    # AWS Lambda container image
        ├── Makefile                      # install, run, test, clean
        ├── requirements.txt              # Python dependencies
        ├── requirements-optional.txt     # DB drivers (pymongo, psycopg2, pymysql)
        ├── .env.example                  # All environment variables with defaults
        │
        ├── src/
        │   ├── app.py                    # FastAPI app, all routes, Lambda handler
        │   ├── config.py                 # Environment-driven config + Secrets Manager
        │   ├── handlers.py               # Business logic (parsing, AI, aggregation)
        │   ├── metrics.py                # CloudWatch custom metrics
        │   └── adapters/
        │       ├── ai.py                 # Hybrid AI classifier (Bedrock + rules + fallback)
        │       ├── chatbot.py            # Streaming chatbot with tool calling & memory
        │       ├── factory.py            # Adapter factory (auto-selects backends)
        │       ├── storage.py            # S3Storage + LocalStorage
        │       └── userstore.py          # 5 database adapters
        │
        ├── frontend/
        │   ├── package.json              # React 19, Vite 8, Recharts, Cognito
        │   ├── vite.config.js
        │   └── src/
        │       ├── App.jsx               # Main dashboard (charts, tables, upload, auth)
        │       ├── auth/cognito.js       # Cognito authentication
        │       └── components/
        │           ├── AuthPage.jsx      # Login / Register / Confirm UI
        │           ├── Chatbot.jsx       # Floating AI chatbot with SSE streaming
        │           └── Chatbot.css
        │
        ├── sample_data/
        │   ├── bank_statement_q2_2026.csv   # Full quarter, ~80 transactions
        │   ├── smoke_test_5_rows.csv        # Minimal test file
        │   ├── bank_statement_sample.pdf    # Sample PDF
        │   └── create.py                    # PDF generator script
        │
        ├── scripts/
        │   └── evaluate_ai.py            # AI accuracy evaluation (30+ test cases)
        │
        └── tests/
            └── test_smoke.py             # 12 smoke tests (health, upload, chat, budgets)
```

---

## Getting Started

### Prerequisites

- **Python 3.12+**
- **Node.js 18+** and npm
- **Git**

No AWS account needed for local development.

### Local Development

```bash
# Clone the repository
git clone https://github.com/your-org/ai-fintech-budget-automation.git
cd ai-fintech-budget-automation/starter_apps/budgetbot

# Create and activate virtual environment
python3 -m venv .venv
# macOS / Linux:
source .venv/bin/activate
# Windows:
.venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Configure environment
cp .env.example .env
# Edit .env if needed — defaults work out of the box

# Start the backend server
uvicorn src.app:app --reload --port 8000
```

The API is now running at **http://localhost:8000** with interactive docs at **http://localhost:8000/docs**.

Health check:
```bash
curl http://localhost:8000/health
```

### Frontend Development

In a separate terminal:

```bash
cd starter_apps/budgetbot/frontend
npm ci
npm run dev
```

The frontend dev server runs at **http://localhost:5173** with hot module replacement.

> When `SERVE_FRONTEND=true` (default), the backend also serves the built frontend at **http://localhost:8000**.

### Running Tests

```bash
cd starter_apps/budgetbot
pytest -v
```

This runs **12 smoke tests** covering:

| # | Test | What it verifies |
|---|------|-----------------|
| 1 | `test_health` | Health endpoint returns correct backend info |
| 2 | `test_upload_csv_categorizes` | CSV upload parses rows and correctly categorizes transactions |
| 3 | `test_summary_aggregates_per_category` | Summary aggregation and top spending drivers |
| 4 | `test_summary_with_month_filter` | Month filtering works correctly |
| 5 | `test_budget_status_uses_abs_spending` | Budget exceeded alerts and per-month filtering |
| 6 | `test_transactions_isolated_per_user` | User data isolation between accounts |
| 7 | `test_chat_memory_isolated_per_user` | Chat memory isolation between users |
| 8 | `test_clear_transactions_clears_chat_memory` | Clearing transactions also clears chat memory |
| 9 | `test_chat_with_no_transactions` | Empty data handling resets stale memory |
| 10 | `test_chat_endpoint_uses_month_filter` | Chat respects month filter |
| 11 | `test_chat_persists_server_side_memory` | Chat messages persist in database |
| 12 | `test_chat_reset_clears_session` | Session-scoped chat reset |

---

## Configuration

All configuration is via environment variables. Copy `.env.example` to `.env` and modify as needed:

| Variable | Description | Default |
|----------|-------------|---------|
| `AI_BACKEND` | AI engine: `local` (rule-based) or `bedrock` (LLM) | `local` |
| `AI_MODEL_ID` | Bedrock model ID | `anthropic.claude-3-5-haiku-20241022-v1:0` |
| `AWS_REGION` | AWS region for all services | `ap-southeast-1` |
| `STORAGE_BACKEND` | File storage: `local` or `s3` | `local` |
| `STORAGE_BUCKET` | S3 bucket name (required if `STORAGE_BACKEND=s3`) | — |
| `USERSTORE_BACKEND` | Database: `sqlite` · `postgres` · `dynamodb` · `documentdb` · `mysql` | `sqlite` |
| `USERSTORE_POSTGRES_URL` | PostgreSQL connection URL | — |
| `SQS_QUEUE_URL` | SQS queue URL for async file processing | — |
| `SERVE_FRONTEND` | Serve frontend static files from backend | `true` |
| `CORS_ORIGINS` | CORS allowed origins | `*` |
| `DEFAULT_USER_ID` | Fallback user ID for local development | `test-user-001` |
| `DB_SECRET_NAME` | AWS Secrets Manager secret for auto-loading DB credentials | — |

> **Tip:** See [`.env.example`](starter_apps/budgetbot/.env.example) for the full list with inline comments.

---

## API Reference

All endpoints are defined in [`src/app.py`](starter_apps/budgetbot/src/app.py). Full interactive documentation is available at `/docs` when the server is running.

**Authentication:** All endpoints (except `/health` and `/`) require either:
- `Authorization: Bearer <JWT>` (production — AWS Cognito)
- `X-User-Id: <user-id>` header (local development)

### Core Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| `GET` | `/health` | Health check — returns backend configuration |
| `GET` | `/` | Serve frontend (when `SERVE_FRONTEND=true`) |

### File Upload & Processing

| Method | Endpoint | Description |
|--------|----------|-------------|
| `POST` | `/upload` | Upload CSV/PDF via multipart form (legacy flow) |
| `POST` | `/upload-request` | Get presigned S3 URL for direct upload |
| `POST` | `/process` | Process a file stored in S3 (synchronous) |
| `POST` | `/enqueue` | Enqueue file for async SQS processing |
| `GET` | `/job-status/{job_id}` | Poll async job status (`QUEUED` → `PROCESSING` → `COMPLETED` / `FAILED`) |

### Transactions

| Method | Endpoint | Description |
|--------|----------|-------------|
| `GET` | `/transactions` | List transactions (optional `?month=YYYY-MM`) |
| `POST` | `/transactions` | Add a manual transaction |
| `PATCH` | `/transactions/{txn_id}` | Update transaction category |
| `DELETE` | `/transactions/{txn_id}` | Delete a single transaction |
| `DELETE` | `/transactions` | Clear all transactions for current user |

### Budgets & Summary

| Method | Endpoint | Description |
|--------|----------|-------------|
| `GET` | `/summary` | Spending summary by category (optional `?month=YYYY-MM`) |
| `GET` | `/budgets` | Get budget status with progress bars and alerts |
| `POST` | `/budgets` | Set budget limit for a category |

### AI Chatbot

| Method | Endpoint | Description |
|--------|----------|-------------|
| `POST` | `/chat` | Chat with AI Money Coach (SSE streaming response) |
| `POST` | `/chat/reset` | Reset current chat session memory |

---

## AI Classification Pipeline

BudgetBot uses a **three-tier hybrid pipeline** to classify transactions:

```
Transaction Input
       │
       ▼
┌──────────────┐     Match?     ┌────────────────┐
│  1. Keyword  │ ──── Yes ────▶ │ Return Category │
│    Rules     │                └────────────────┘
└──────┬───────┘
       │ No (ambiguous)
       ▼
┌──────────────┐     Match?     ┌────────────────┐
│  2. Bedrock  │ ──── Yes ────▶ │ Return Category │
│    LLM       │                └────────────────┘
└──────┬───────┘
       │ Error / Timeout
       ▼
┌──────────────┐                ┌────────────────┐
│  3. Local    │ ─────────────▶ │ Return Category │
│    Fallback  │                └────────────────┘
└──────────────┘
```

**1. Rule-Based Engine** — Fast keyword matching for clear-cut transactions (e.g., "Grab" → Transportation, "Netflix" → Subscriptions). Zero latency, zero cost.

**2. LLM Classification** — Amazon Bedrock (Claude 3.5 Haiku or Amazon Nova) handles ambiguous transactions via the Converse API. User correction history is injected as high-confidence examples into the prompt for personalization.

**3. Local Fallback** — A secondary rule-based classifier activates if Bedrock is unavailable, ensuring the system never fails.

### Chatbot Capabilities

The AI Money Coach (`/chat`) goes beyond simple Q&A:

- **Streaming responses** via Server-Sent Events (SSE)
- **Persistent memory** in the database (survives page reloads)
- **Rolling memory summarization** to control token usage
- **Tool calling** — can write to the database (e.g., `set_budget`)
- **Domain guardrails** — refuses non-financial questions
- **Empty data handling** — guides new users to upload statements

Run the AI evaluation script to measure classification accuracy:
```bash
python scripts/evaluate_ai.py
```

---

## Deployment

### AWS Production Deployment

The project includes a complete CI/CD pipeline via GitHub Actions.

**Push to `main`** triggers:

1. **Backend:** Docker image build → push to Amazon ECR → Lambda function update
2. **Frontend:** `npm run build` → sync to S3 → CloudFront cache invalidation

**AWS Services Used:**

| Service | Role |
|---------|------|
| AWS Lambda | Serverless compute (container image from ECR) |
| Amazon ECR | Docker image registry |
| Amazon S3 | File uploads + frontend static hosting |
| Amazon SQS + DLQ | Async file processing queue |
| Amazon RDS (PostgreSQL) | Production database |
| Amazon Bedrock | LLM inference |
| Amazon CloudFront + WAF | CDN + web application firewall |
| AWS Cognito | User authentication (JWT) |
| API Gateway v2 | HTTP API with JWT authorizer |
| Amazon CloudWatch | Custom metrics, alarms, dashboards |
| VPC + Private Subnets | Network isolation with VPC endpoints |
| Route 53 + ACM | Custom domain with HTTPS |
| AWS Secrets Manager | Database credential rotation |

### Manual Deployment

```bash
# Switch to production mode in .env
AI_BACKEND=bedrock
STORAGE_BACKEND=s3
USERSTORE_BACKEND=postgres
STORAGE_BUCKET=your-bucket-name
SQS_QUEUE_URL=https://sqs.ap-southeast-1.amazonaws.com/xxx/your-queue

# Build and push Docker image
docker build -t budgetbot .
docker tag budgetbot:latest <account>.dkr.ecr.ap-southeast-1.amazonaws.com/budgetbot:latest
docker push <account>.dkr.ecr.ap-southeast-1.amazonaws.com/budgetbot:latest

# Build frontend
cd frontend && npm run build
aws s3 sync dist/ s3://your-frontend-bucket/
aws cloudfront create-invalidation --distribution-id XXX --paths "/*"
```

---

## Evaluation

For XBrain program participants, evaluation criteria include:

| Criterion | Description |
|-----------|-------------|
| **Group Presentation** | Architecture quality, AWS design decisions, deployment demo |
| **Individual Q&A** | Ability to explain technical decisions during presentations |
| **Daily Checkpoints** | Kahoot quizzes and activities during Mon–Wed sessions |
| **Peer Evaluation** | Teammate contribution ratings |
| **Classroom Participation** | Daily engagement tracking |

### Weekly Program Structure

| Week | Theme | Focus |
|------|-------|-------|
| W1 | Propose & Map | Architecture diagrams, on-prem to AWS mapping |
| W2 | Storage & Identity | S3, EBS, IAM, VPC |
| W3 | Database & AI | RDS, DynamoDB, Bedrock |
| W4 | Data Pipelines | ETL, analytics, ML pipelines |
| W5 | Networking | VPC hardening, API Gateway, WAF |
| W6 | Operations & Security | CloudWatch, auto-scaling, KMS |
| W7 | **Capstone Hackathon** | Ship production-ready AI in 48 hours |

---

## Contributing

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

Please ensure all tests pass before submitting:
```bash
pytest -v
```

---

## License

This project is part of the **XBrain AWS DevOps/CloudOps Foundation Program**.

Sample data for BudgetBot uses synthetic Vietnamese transactions under the **CC0 (Public Domain)** license.

External data sources in other starter apps are cited in their respective `sample_data/SOURCES.md` files.

---

<div align="center">

**Built with ❤️ by the XBrain Team**

</div>
