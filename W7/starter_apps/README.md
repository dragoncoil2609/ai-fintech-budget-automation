# W7 Starter Apps — 3 Reference Source Codes

This directory contains 3 complete, runnable application sources for the W7 Capstone Hackathon. Pick **one** domain per group. The code works on your laptop today without any AWS account, then deploys to AWS by switching env vars.

| App | Domain | Tech | Local stack | Production stack (group chooses) |
|-----|--------|------|-------------|----------------------------------|
| [`studybot/`](./studybot/) | EduTech — AI Study Buddy | RAG (vector retrieval) | SQLite + filesystem + in-memory vector + AI stub | Bedrock KB + Haiku + (your DB, your hosting, your network) |
| [`budgetbot/`](./budgetbot/) | FinTech — AI Money Coach | Direct LLM call (no RAG) | SQLite + filesystem + rule-based stub | Bedrock InvokeModel + Haiku + (your DB, your hosting) |
| [`dochub/`](./dochub/) | ProductivityTech — AI Document Hub | RAG + multi-tenancy | SQLite + filesystem + in-memory vector + AI stub | Bedrock Agent + KB with tenant filter + (your DB, your hosting) |

---

## 📚 Sample data sources (citations)

| App | Sample data source | License | Full citation |
|-----|-------------------|---------|---------------|
| **studybot** | HuggingFace [`wikimedia/wikipedia`](https://huggingface.co/datasets/wikimedia/wikipedia) config `20231101.simple` | CC-BY-SA-4.0 | [`studybot/sample_data/SOURCES.md`](./studybot/sample_data/SOURCES.md) |
| **dochub** | HuggingFace [`coastalcph/lex_glue`](https://huggingface.co/datasets/coastalcph/lex_glue) config `ledgar` (LEDGAR provisions from SEC EDGAR filings) | CC-BY-4.0 | [`dochub/sample_data/SOURCES.md`](./dochub/sample_data/SOURCES.md) |
| **budgetbot** | Synthetic Vietnamese transactions (NOT from HuggingFace — surveyed HF, no clean Vietnamese transaction dataset exists) | CC0 / public domain | [`budgetbot/sample_data/README.md`](./budgetbot/sample_data/README.md) |

Re-generate any dataset: `python3 tooling/fetch_w7_datasets.py --app studybot|dochub|budgetbot|all`

Each sample file in `studybot/` and `dochub/` has source URL + dataset name embedded in the file header (`_Source: HuggingFace ...`). BudgetBot CSVs don't claim a HF source — provenance is in its `README.md`.

---

## Philosophy — Why source code is provided

W7 is a **DevOps/CloudOps** assessment, not a software engineering one. The grading rubric weights:

| Criterion | Weight | Tests |
|-----------|--------|-------|
| I — Original Arch | 10% | Domain rationale + customizations on top of provided code |
| II — AWS Architecture | 20% | **Your service choices for deploying this code** |
| III — Individual QnA | 30% | Why those choices? Walk me through the code |
| IV — Working Deployment + Evidence | 40% | URL works + Evidence Pack + cost discipline |

→ **70% of your grade is on AWS deployment + ops, not on writing the code.**

So we hand you working application code. You decide **how to run it on AWS**.

---

## What's PRESERVED — 9 service choices stay yours

The code is intentionally written so the following are still **your decisions**:

| # | Decision | How it stays open |
|---|----------|-------------------|
| 1 | **Compute runtime** — Lambda vs ECS Fargate vs EC2 vs App Runner | Code is FastAPI → runs in all 4 runtimes (use Mangum adapter for Lambda, or uvicorn for the rest) |
| 2 | **User-state database** — DynamoDB vs RDS Postgres vs RDS MySQL vs Aurora vs DocumentDB vs SQLite | **5 adapters provided**: `dynamodb` / `postgres` / `mysql` / `documentdb` / `sqlite`. Set `USERSTORE_BACKEND` to pick. Adding more (Neptune, MemoryDB, etc.) is fair game — see `src/adapters/userstore.py` for the interface. |
| 3 | **Vector store backend** — OpenSearch Serverless vs S3 Vectors vs Aurora pgvector vs Pinecone | Code uses Bedrock KB → you pick the vector backend when creating the KB in console |
| 4 | **Frontend hosting** — CloudFront+S3 vs Amplify vs ALB+EC2 vs same compute as backend | Frontend is plain HTML/JS with `window.API_BASE` override → host it anywhere. Backend's `/` route is opt-out via `SERVE_FRONTEND=false` env var. CORS middleware allows cross-origin requests. |
| 5 | **Identity** — Cognito User Pool vs IAM-only vs hardcoded test user vs signed URL | Code expects `X-User-Id` header. You decide who populates it. |
| 6 | **VPC topology** — subnet layout, SG rules, NAT vs VPC Endpoints | Code knows nothing about VPC. Your design entirely. |
| 7 | **IaC** — Console click vs CloudFormation vs CDK vs Terraform vs SAM | Code is not coupled to any IaC tool. |
| 8 | **Observability** — CloudWatch dashboard, alarms, custom metrics, X-Ray | Code emits via `boto3.client('cloudwatch').put_metric_data()`. You design dashboards + alarms. |
| 9 | **Cost optimization** — instance sizing, reserved vs on-demand, single-AZ vs multi-AZ | Entirely your decision. |

---

## What's FIXED — and why that's OK

These are coupled in the code, by design:

| Fixed | Why |
|-------|-----|
| **AI vendor = Bedrock** | W3-W4 taught Bedrock. Swapping to OpenAI would be off-curriculum. |
| **Object storage = S3** | W2 taught S3. Core skill. |
| **HTTP framework = FastAPI** | Not graded; framework choice is incidental. |
| **Language = Python** | Not graded; language choice is incidental. |

You can change these, but no bonus credit for doing so. Use the time to nail the 9 open decisions.

---

## 3 deploy patterns (frontend & backend split or not)

The starter supports all common topologies. The code has no opinion on which you pick.

### Pattern A — Backend serves frontend (simplest, single origin)

```
[ Browser ] → [ CloudFront ] → [ ALB / API Gateway ] → [ Lambda / ECS / EC2 ]
                                                          ├─ FastAPI app
                                                          └─ GET /          (returns frontend/index.html)
                                                              POST /upload  /query  /docs/list  ...
```
Set `SERVE_FRONTEND=true` (default). Frontend fetch uses relative URLs (`/upload`).

### Pattern B — Frontend on CloudFront+S3, backend on API Gateway (recommended for production)

```
[ Browser ] → CloudFront with TWO origins:
                ├─ S3 bucket (static)              → frontend/index.html
                └─ API Gateway behavior /api/*     → Lambda / ECS

Configure CloudFront origin behaviors so /api/* hits backend, everything else hits S3.
```
Set `SERVE_FRONTEND=false` on backend. In the static HTML, set the API base via either:
```html
<script>window.API_BASE = '/api';</script>           <!-- inside index.html before main script -->
```
or open the page with `?api=https://api.example.com` query param.

### Pattern C — Frontend on Amplify (or separate ALB), backend on API Gateway / ALB

```
[ Browser ] → Amplify Hosting        → frontend/index.html
              │
              └─ JS fetches https://api.example.com → API Gateway → Lambda / ECS
```
Set `SERVE_FRONTEND=false`. Backend must allow CORS from the Amplify domain: set `CORS_ORIGINS=https://main.dXYZ.amplifyapp.com`. Frontend sets `window.API_BASE = 'https://api.example.com'`.

CORS is enabled by default with `CORS_ORIGINS=*` (permissive — hackathon). Pin it to your real frontend URL in production.

---

## Quickstart — run locally in 2 minutes

```bash
cd outputs/W7/starter_apps/studybot       # or budgetbot, or dochub

python3 -m venv .venv
source .venv/bin/activate                  # Windows: .venv\Scripts\activate
pip install -r requirements.txt

cp .env.example .env                       # defaults to LOCAL_MODE everything
uvicorn src.app:app --reload --port 8000

# In another terminal:
curl http://localhost:8000/health
open http://localhost:8000                 # browser UI
```

No AWS credentials needed. The app uses local SQLite + filesystem + an AI stub that echoes back canned responses.

When you're ready to deploy, edit `.env`:

```diff
- AI_BACKEND=local
+ AI_BACKEND=bedrock
- STORAGE_BACKEND=local
+ STORAGE_BACKEND=s3
- USERSTORE_BACKEND=sqlite
+ USERSTORE_BACKEND=dynamodb           # or postgres
- VECTOR_BACKEND=local
+ VECTOR_BACKEND=bedrock_kb
```

Plus set AWS service identifiers (bucket name, KB ID, table name, etc.) — see `.env.example` in each app.

---

## File structure (same in all 3 apps)

```
{app}/
├── README.md             — what the code does, how to run locally, deploy hints
├── requirements.txt      — Python dependencies
├── .env.example          — all env vars with defaults for LOCAL_MODE
├── Makefile              — convenience: make install, make run, make test
├── src/
│   ├── app.py            — FastAPI app + routes
│   ├── config.py         — reads all config from env
│   ├── handlers.py       — endpoint handler functions
│   └── adapters/
│       ├── ai.py         — BedrockAI + LocalAI
│       ├── storage.py    — S3Storage + LocalStorage
│       ├── userstore.py  — DynamoDB + Postgres + SQLite adapters
│       ├── vector.py     — Bedrock KB + Local vector (studybot/dochub only)
│       └── factory.py    — picks adapter based on env
├── frontend/index.html   — plain HTML/JS UI
├── sample_data/          — sample inputs for local testing
└── tests/test_smoke.py   — basic sanity tests
```

---

## Customization — what to add on top (for Criterion I — 10%)

The provided code is a baseline. Your team should add **at least one** customization to demonstrate ownership:

- **StudyBot:** spaced-repetition scheduler, difficulty levels for quizzes, multi-language support, voice input
- **BudgetBot:** budget goals + alerts, recurring transaction detection, multi-currency, forecasting
- **DocHub:** document version control, commenting/annotations, scheduled re-ingestion, document-level ACLs beyond tenant

Document your customization in `docs/W7_evidence.md` section 7 (Lessons Learned). Trainers will ask about it.

---

## What to commit to your GitHub repo

```
your-team-repo/
├── src/                  — your modified copy of one starter app
├── frontend/             — your modified frontend
├── infrastructure/       — YOUR IaC choice (CFN/CDK/Terraform/whatever)
├── docs/
│   ├── W7_evidence.md    — the graded artifact (Cover, Architecture, Cost, Security, Monitoring, etc.)
│   ├── architecture.png  — your diagram
│   └── teardown_confirmation.md   — committed after Sun 1/6 EOD
└── README.md             — how to deploy YOUR version (not the stock starter)
```

Good luck. Ship it.
