# DocHub — W7 Capstone Starter

**Domain:** ProductivityTech. Multi-tenant document Q&A. Each organization (`tenant_id`) only sees and queries its own documents. Critical security property: **a bug in handler code cannot leak cross-tenant data** — isolation is enforced at the retrieval layer.

Runs **fully locally** with in-memory vector index + SQLite. Switch to Bedrock KB + tenant-filtered retrieval in production.

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

# End-to-end smoke (note BOTH X-Tenant-Id and X-User-Id headers):
curl -X POST http://localhost:8000/upload \
  -H "X-Tenant-Id: tenant-acme" -H "X-User-Id: alice" \
  -F "file=@sample_data/acme_contract.txt" -F "doc_type=contract"

curl -X POST http://localhost:8000/query \
  -H "X-Tenant-Id: tenant-acme" -H "X-User-Id: alice" \
  -H "Content-Type: application/json" \
  -d '{"question":"What is the termination notice period?"}'
```

Run tests (includes a critical **tenant isolation** test):
```bash
pytest -v
```

---

## What's in the code

```
src/
├── app.py               FastAPI app — requires X-Tenant-Id + X-User-Id headers
├── config.py            Env-driven config
├── handlers.py          Tenant-aware business logic
└── adapters/
    ├── ai.py            BedrockAI (RAG with tenant filter) | LocalAI (stub)
    ├── storage.py       S3Storage | LocalStorage (tenant_id is in S3 key prefix)
    ├── userstore.py     DynamoDB (PK=tenant_id) | Postgres | SQLite
    ├── vector.py        Bedrock KB (filter on tenant_id metadata) | LocalVector
    └── factory.py
```

**Tenant isolation enforced at 4 layers (defense in depth):**

| Layer | How |
|-------|-----|
| **Storage** | S3 key prefix = `<tenant_id>/<doc_id>/<filename>`. Apply IAM `aws:PrincipalTag/tenant` condition for hard enforcement. |
| **Document metadata DB** | PK = `tenant_id`. Cross-tenant query impossible without rewriting the access pattern. |
| **Vector store** | Every retrieve call filters `metadata.tenant_id`. Bug in handler code cannot leak across tenants because retrieval itself is filtered. |
| **AI prompt** | System prompt says "ONLY use documents from {tenant_id}". Belt + suspenders. |

---

## 9 deployment decisions still yours

Same matrix as the other apps. Notable for DocHub:

- **Identity is non-trivial:** how do you populate `X-Tenant-Id`? Cognito User Pool with custom attribute `custom:tenant_id` → API Gateway authorizer Lambda → decode JWT and inject header. Or simpler: pre-token Lambda that maps user → tenant. This is a real architecture decision worth 5 minutes of QnA.
- **Vector store filtering:** Bedrock KB supports metadata filtering across OpenSearch Serverless / S3 Vectors / Aurora pgvector. You pick which backend, but the filter syntax is the same.
- **Bedrock Agent (optional):** the code currently uses `retrieve_and_generate`. To use a Bedrock Agent with action groups, swap the call to `invoke_agent` and define an action group Lambda. Bonus feature opportunity.

---

## Deploy hints

```diff
- AI_BACKEND=local
+ AI_BACKEND=bedrock

- STORAGE_BACKEND=local
+ STORAGE_BACKEND=s3
+ STORAGE_BUCKET=dochub-tenant-docs-g<N>

- USERSTORE_BACKEND=sqlite
+ USERSTORE_BACKEND=dynamodb           # PK=tenant_id natural fit
+ USERSTORE_TABLE=dochub-documents

- VECTOR_BACKEND=local
+ VECTOR_BACKEND=bedrock_kb
+ VECTOR_BEDROCK_KB_ID=ABCDEFG123
```

**KB ingestion gotcha:** Bedrock KB ingests from S3. To make tenant_id metadata work, you must write a `<file>.metadata.json` sidecar next to each uploaded file with `{"metadataAttributes":[{"key":"tenant_id","value":{"type":"STRING","stringValue":"<tenant>"}}]}`. Then trigger KB sync. **Document this pipeline in your Evidence Pack.**

---

## Customization ideas (Criterion I)

- **Version control** — upload v2 of a contract, store both, default to latest. Adds DynamoDB SK suffix.
- **ACL beyond tenant** — within a tenant, restrict docs to specific user IDs (`owner` field; user can only query own docs unless `share_with` is set).
- **Approval workflow** — Step Functions state machine: upload → review → publish.
- **Annotations** — endpoint `POST /docs/{doc_id}/annotation` storing comments per chunk.
- **Bedrock Agent action group** — natural-language commands like "show me all contracts from last month" → tool call.
- **Scheduled re-ingestion** — EventBridge schedule re-syncs Confluence/SharePoint into KB nightly.

---

## Sample data (for testing isolation)

```bash
# Upload as ACME
curl -X POST http://localhost:8000/upload \
  -H "X-Tenant-Id: tenant-acme" -H "X-User-Id: alice" \
  -F "file=@sample_data/acme_contract.txt" -F "doc_type=contract"

# Upload as Globex
curl -X POST http://localhost:8000/upload \
  -H "X-Tenant-Id: tenant-globex" -H "X-User-Id: bob" \
  -F "file=@sample_data/globex_policy.txt" -F "doc_type=policy"

# ACME asks about Globex data — should return "could not find"
curl -X POST http://localhost:8000/query \
  -H "X-Tenant-Id: tenant-acme" -H "X-User-Id: alice" \
  -H "Content-Type: application/json" \
  -d '{"question":"What is the data retention policy?"}'

# Globex asks about its OWN data — should return citations
curl -X POST http://localhost:8000/query \
  -H "X-Tenant-Id: tenant-globex" -H "X-User-Id: bob" \
  -H "Content-Type: application/json" \
  -d '{"question":"How long do we keep email?"}'
```
