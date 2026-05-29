# BudgetBot — W7 Capstone Starter

**Domain:** FinTech. Upload bank statement CSV → AI categorizes each transaction → spending summary by category.

Runs **fully locally** with rule-based categorization stub. Flip env vars to use Bedrock Haiku in production.

---

## Run locally (2 minutes)

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt

cp .env.example .env
uvicorn src.app:app --reload --port 8000

# In another terminal:
curl http://localhost:8000/health
open http://localhost:8000

# End-to-end smoke:
curl -X POST http://localhost:8000/upload \
  -H "X-User-Id: alice" \
  -F "file=@sample_data/sample_statement.csv"

curl "http://localhost:8000/summary?month=2026-05" \
  -H "X-User-Id: alice"
```

Run tests:
```bash
pytest -v
```

---

## What's in the code

```
src/
├── app.py               FastAPI app + routes. Runs on Lambda, ECS, EC2, App Runner.
├── config.py            Env-driven settings.
├── handlers.py          CSV parsing + categorization orchestration + aggregation.
└── adapters/
    ├── ai.py            BedrockAI (real InvokeModel Converse) | LocalAI (rule-based)
    ├── storage.py       S3Storage | LocalStorage (filesystem)
    ├── userstore.py     DynamoDBUserStore | PostgresUserStore | SQLiteUserStore
    └── factory.py       Picks adapter based on env
```

**No vector store** — BudgetBot uses direct InvokeModel for one-shot classification. This is a key architecture difference from StudyBot and DocHub (which use RAG).

---

## 9 deployment decisions still yours

Same matrix as the other apps. Notable points for BudgetBot:

- **DB choice trade-off:** Aggregations like `SELECT category, SUM(amount) FROM transactions WHERE user_id=? GROUP BY category` are natural fits for SQL (Postgres). DynamoDB requires a Scan or careful GSI design. Document this trade-off in your Evidence Pack.
- **RDS Proxy:** With Lambda + Postgres, you'll want RDS Proxy to handle connection pooling. The code uses `psycopg2.connect()` — Lambda containers each open their own connection.
- **Cost:** RDS db.t3.micro (~$1.25/48h in Singapore) is the biggest fixed cost. Single-AZ. Skip Multi-AZ for hackathon.

---

## Deploy hints

Env flip:
```diff
- AI_BACKEND=local
+ AI_BACKEND=bedrock
+ AI_MODEL_ID=anthropic.claude-3-5-haiku-20241022-v1:0

- STORAGE_BACKEND=local
+ STORAGE_BACKEND=s3
+ STORAGE_BUCKET=budgetbot-statements-g<N>-<accountid>

- USERSTORE_BACKEND=sqlite
+ USERSTORE_BACKEND=postgres          # OR dynamodb
+ USERSTORE_POSTGRES_URL=postgresql://user:pw@your-rds-endpoint:5432/budgetbot
```

For DynamoDB, set `USERSTORE_TABLE=...` instead of the postgres URL.

Lambda packaging: wrap `from src.app import app` with `Mangum` (`pip install mangum`).

---

## Customization ideas (Criterion I)

- **Budget goals + alerts** — let users set "max $200/month on Food" with SNS notification when crossed
- **Recurring transaction detection** — flag subscriptions automatically (Netflix, Spotify, etc.)
- **Multi-currency** — detect VND vs USD, convert on the fly
- **Forecasting** — given 2 months of data, predict next month per category
- **Anomaly detection** — flag transactions >2σ from category mean (real-time use case for AWS Lookout for Metrics OR a simple Lambda)
- **Receipt OCR** — accept PDF receipts, extract via Textract → categorize

---

## Sample CSV format

```
date,description,amount
2026-05-02,Highlands Coffee - Bui Vien,-65000
2026-05-04,Salary deposit credit,18500000
```

Header row optional. Negative amounts = expenses; positive = income. Currency assumed VND in the local stub but Bedrock doesn't care — describe the transaction and the LLM figures it out.
