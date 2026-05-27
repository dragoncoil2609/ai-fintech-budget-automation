"""FastAPI app for DocHub. Tenant header is required on every request."""
from pathlib import Path
from typing import Optional

from fastapi import FastAPI, File, Form, Header, HTTPException, UploadFile
from fastapi.responses import FileResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from src.config import config
from src.adapters import factory
from src import handlers


app = FastAPI(title="DocHub — W7 Capstone Starter")


# CORS — allow frontend to live on a different origin (CloudFront / Amplify / separate ALB).
# CORS_ORIGINS env var controls this; default '*' is permissive for hackathon.
_allowed = ["*"] if config.cors_origins == "*" else [o.strip() for o in config.cors_origins.split(",") if o.strip()]
app.add_middleware(
    CORSMiddleware,
    allow_origins=_allowed,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

ai_client = factory.make_ai()
storage = factory.make_storage()
userstore = factory.make_userstore()
vector_store = factory.make_vector()


def _resolve_identity(x_user_id: Optional[str], x_tenant_id: Optional[str]) -> tuple:
    user_id = x_user_id or config.default_user_id
    tenant_id = x_tenant_id or config.default_tenant_id
    return user_id, tenant_id


class QueryRequest(BaseModel):
    question: str


@app.get("/health")
def health() -> dict:
    return {
        "status": "ok",
        "backends": {
            "ai": config.ai_backend,
            "storage": config.storage_backend,
            "userstore": config.userstore_backend,
            "vector": config.vector_backend,
        },
    }


@app.post("/upload")
async def upload(
    file: UploadFile = File(...),
    doc_type: str = Form(default="general"),
    x_user_id: Optional[str] = Header(default=None),
    x_tenant_id: Optional[str] = Header(default=None),
) -> dict:
    user_id, tenant_id = _resolve_identity(x_user_id, x_tenant_id)
    data = await file.read()
    if not data:
        raise HTTPException(status_code=400, detail="Empty file")
    return handlers.handle_upload(
        tenant_id=tenant_id,
        user_id=user_id,
        filename=file.filename or "untitled",
        doc_type=doc_type,
        data=data,
        storage=storage,
        userstore=userstore,
        vector_store=vector_store,
    )


@app.post("/query")
def query(
    req: QueryRequest,
    x_user_id: Optional[str] = Header(default=None),
    x_tenant_id: Optional[str] = Header(default=None),
) -> dict:
    _, tenant_id = _resolve_identity(x_user_id, x_tenant_id)
    if not req.question.strip():
        raise HTTPException(status_code=400, detail="Empty question")
    return handlers.handle_query(
        tenant_id=tenant_id,
        question=req.question,
        ai_client=ai_client,
        vector_store=vector_store,
        vector_backend=config.vector_backend,
        bedrock_kb_id=config.vector_bedrock_kb_id,
    )


@app.get("/docs/list")
def list_docs(
    doc_type: Optional[str] = None,
    x_user_id: Optional[str] = Header(default=None),
    x_tenant_id: Optional[str] = Header(default=None),
) -> dict:
    _, tenant_id = _resolve_identity(x_user_id, x_tenant_id)
    return handlers.handle_list_docs(tenant_id, doc_type, userstore)


# ---- Static frontend ----
FRONTEND_DIR = Path(__file__).resolve().parent.parent / "frontend"


if config.serve_frontend:
    @app.get("/")
    def index() -> FileResponse:
        """Convenience: serves frontend/index.html at /. Set SERVE_FRONTEND=false
        if you deploy the frontend separately (CloudFront+S3, Amplify, ALB)."""
        return FileResponse(FRONTEND_DIR / "index.html")
