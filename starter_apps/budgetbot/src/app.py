"""FastAPI app for BudgetBot. Runtime-agnostic."""
from pathlib import Path
from typing import Optional, List

import boto3
import uuid

from fastapi import FastAPI, File, Header, HTTPException, Request, UploadFile
from fastapi.responses import FileResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from .config import config
from .adapters import factory
from .adapters.chatbot import ChatbotAI
from . import handlers
from .metrics import put_metric
# Import Mangum to wrap FastAPI for AWS Lambda
try:
    from mangum import Mangum  # type: ignore
except ImportError:
    Mangum = None


app = FastAPI(title="BudgetBot — W7 Capstone Starter")


@app.middleware("http")
async def strip_api_prefix(request, call_next):
    path = request.scope.get("path", "")
    if path.startswith("/api"):
        request.scope["path"] = path[4:] or "/"
    return await call_next(request)


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
chatbot_client = ChatbotAI(region=config.aws_region, model_id=config.ai_model_id)


def _resolve_user_id(request, x_user_id: Optional[str] = None) -> str:
    """Lấy user_id thực từ JWT Claims (Cognito sub) do API Gateway v2 nhúng vào.
    
    Khi API Gateway xác thực JWT thành công, nó nhúng claims vào:
    event["requestContext"]["authorizer"]["jwt"]["claims"]["sub"]
    Mangum chuyển event này vào request.scope["aws.event"].
    
    Fallback: X-User-Id header (local dev) hoặc config.default_user_id.
    """
    try:
        event = request.scope.get("aws.event", {})
        sub = (
            event.get("requestContext", {})
                 .get("authorizer", {})
                 .get("jwt", {})
                 .get("claims", {})
                 .get("sub")
        )
        if sub:
            return sub
    except Exception:
        pass
    return x_user_id or config.default_user_id



# ── Health ────────────────────────────────────────────────────────────────────

@app.get("/health")
def health() -> dict:
    return {
        "status": "ok",
        "backends": {
            "ai": config.ai_backend,
            "storage": config.storage_backend,
            "userstore": config.userstore_backend,
        },
    }


# ── Upload (legacy — file đi qua Lambda) ─────────────────────────────────────

@app.post("/upload")
async def upload(
    request: Request,
    file: UploadFile = File(...),
    x_user_id: Optional[str] = Header(default=None),
) -> dict:
    """Luồng upload cũ: file đi qua Lambda (multipart). Giữ nguyên cho local dev / fallback."""
    user_id = _resolve_user_id(request, x_user_id)
    data = await file.read()
    if len(data) > config.max_upload_size:
        raise HTTPException(status_code=413, detail=f"File too large (max {config.max_upload_size // 1024 // 1024} MB)")
    if not data:
        raise HTTPException(status_code=400, detail="Empty file")
    return handlers.handle_upload(
        user_id=user_id,
        filename=file.filename or "statement.csv",
        data=data,
        ai_client=ai_client,
        storage=storage,
        userstore=userstore,
    )


# ── Presigned URL upload (luồng mới — file đi thẳng lên S3) ──────────────────

class UploadRequestBody(BaseModel):
    filename: str


@app.post("/upload-request")
def upload_request(
    request: Request,
    body: UploadRequestBody,
    x_user_id: Optional[str] = Header(default=None),
) -> dict:
    """Bước 1 của luồng Presigned URL:
    Lambda tạo presigned PUT URL + s3_key và trả về cho frontend.
    Frontend dùng URL đó để PUT file trực tiếp lên S3 (không qua Lambda).

    Nếu storage backend không hỗ trợ presigned URL (ví dụ local dev),
    trả về upload_url=null để frontend fallback về /upload.
    """
    user_id = _resolve_user_id(request, x_user_id)
    filename = body.filename or "statement.csv"

    try:
        s3_key = f"uploads/{user_id}/{uuid.uuid4()}/{filename}"
        expiry = config.s3_presign_expiry

        upload_url = storage.generate_presigned_put(key=s3_key, expiry=expiry)

        put_metric(
            "PresignedUrlGenerated",
            1,
            "Count",
            route="/upload-request",
            user_id=user_id,
        )

        return {
            "upload_url": upload_url,
            "s3_key": s3_key,
            "expires_in": expiry,
            "method": "PUT",
            "content_type": "application/octet-stream",
            "fallback_to_multipart": upload_url is None,
        }

    except Exception:
        put_metric(
            "PresignedUrlFailed",
            1,
            "Count",
            route="/upload-request",
            user_id=user_id,
        )
        raise

class ProcessBody(BaseModel):
    s3_key: str
    filename: str
    mapping: Optional[dict] = None


@app.post("/process")
def process(
    request: Request,
    body: ProcessBody,
    x_user_id: Optional[str] = Header(default=None),
) -> dict:
    """Bước 3 của luồng Presigned URL:"""
    user_id = _resolve_user_id(request, x_user_id)

    if not body.s3_key:
        raise HTTPException(status_code=400, detail="s3_key is required")
    if not body.filename:
        raise HTTPException(status_code=400, detail="filename is required")

    try:
        return handlers.handle_process_from_s3(
            user_id=user_id,
            s3_key=body.s3_key,
            filename=body.filename,
            storage=storage,
            ai_client=ai_client,
            userstore=userstore,
            mapping=body.mapping,
        )
    except Exception as exc:
        # handle_process_from_s3 cũng đã emit UploadJobFailed.
        # Ở đây chỉ chuyển lỗi thành HTTP 500 cho frontend.
        raise HTTPException(status_code=500, detail=f"Lỗi xử lý file từ S3: {exc}") from exc

class EnqueueBody(BaseModel):
    s3_key: str
    filename: str
    mapping: Optional[dict] = None


@app.post("/enqueue")
def enqueue(
    request: Request,
    body: EnqueueBody,
    x_user_id: Optional[str] = Header(default=None),
) -> dict:
    """Luồng SQS async."""
    user_id = _resolve_user_id(request, x_user_id)

    if not body.s3_key:
        raise HTTPException(status_code=400, detail="s3_key is required")
    if not body.filename:
        raise HTTPException(status_code=400, detail="filename is required")
    if not config.sqs_queue_url:
        raise HTTPException(status_code=503, detail="SQS_QUEUE_URL chưa được cấu hình")

    try:
        return handlers.handle_enqueue(
            user_id=user_id,
            s3_key=body.s3_key,
            filename=body.filename,
            sqs_queue_url=config.sqs_queue_url,
            userstore=userstore,
            mapping=body.mapping,
        )
    except Exception as exc:
        put_metric(
            "UploadJobFailed",
            1,
            "Count",
            route="/enqueue",
            user_id=user_id,
        )
        raise HTTPException(status_code=500, detail=f"Lỗi enqueue: {exc}") from exc

@app.get("/job-status/{job_id}")
def job_status(
    job_id: str,
    x_user_id: Optional[str] = Header(default=None),
) -> dict:
    """Trả về trạng thái xử lý của job theo job_id.
    Frontend polling endpoint này mỗi 2 giây sau khi enqueue.
    Status: QUEUED → PROCESSING → COMPLETED | FAILED
    """
    return handlers.handle_job_status(job_id=job_id, userstore=userstore)


# ── Chatbot & Budgets ─────────────────────────────────────────────────────────

class ChatBody(BaseModel):
    message: str
    session_id: Optional[str] = None
    month: Optional[str] = None
    history: Optional[List[dict]] = None

from fastapi.responses import StreamingResponse

@app.post("/chat")
def chat(
    request: Request,
    body: ChatBody,
    x_user_id: Optional[str] = Header(default=None),
) -> StreamingResponse:
    generator = handlers.handle_chat(
        _resolve_user_id(request, x_user_id),
        body.message,
        body.session_id,
        body.month,
        userstore,
        chatbot_client,
    )
    return StreamingResponse(generator, media_type="text/event-stream")

@app.get("/budgets")
def get_budgets(
    request: Request,
    x_user_id: Optional[str] = Header(default=None),
) -> dict:
    return handlers.handle_get_budgets(_resolve_user_id(request, x_user_id), userstore)


class BudgetUpdate(BaseModel):
    category: str
    amount: float


@app.post("/budgets")
def set_budget(
    request: Request,
    body: BudgetUpdate,
    x_user_id: Optional[str] = Header(default=None),
) -> dict:
    return handlers.handle_set_budget(_resolve_user_id(request, x_user_id), body.category, body.amount, userstore)


# ── Transactions & Summary ────────────────────────────────────────────────────

@app.get("/summary")
def summary(
    request: Request,
    month: Optional[str] = None,
    x_user_id: Optional[str] = Header(default=None),
) -> dict:
    """`month` format: YYYY-MM. Omit for all-time summary."""
    return handlers.handle_summary(_resolve_user_id(request, x_user_id), month, userstore)


@app.get("/transactions")
def transactions(
    request: Request,
    month: Optional[str] = None,
    x_user_id: Optional[str] = Header(default=None),
) -> dict:
    return handlers.handle_list_transactions(_resolve_user_id(request, x_user_id), month, userstore)


class TransactionCreate(BaseModel):
    date: str
    description: str
    amount: float
    category: Optional[str] = "Other"


@app.post("/transactions")
def add_transaction(
    request: Request,
    body: TransactionCreate,
    x_user_id: Optional[str] = Header(default=None),
) -> dict:
    return handlers.handle_add_transaction(_resolve_user_id(request, x_user_id), body.dict(), userstore, ai_client)


class CategoryUpdate(BaseModel):
    category: str


@app.patch("/transactions/{txn_id}")
def update_category(
    request: Request,
    txn_id: int,
    data: CategoryUpdate,
    x_user_id: Optional[str] = Header(default=None),
) -> dict:
    return handlers.handle_update_category(_resolve_user_id(request, x_user_id), txn_id, data.category, userstore)


@app.delete("/transactions")
def clear_transactions(
    request: Request,
    x_user_id: Optional[str] = Header(default=None),
) -> dict:
    return handlers.handle_clear_transactions(_resolve_user_id(request, x_user_id), userstore)


@app.delete("/transactions/{txn_id}")
def delete_transaction(
    request: Request,
    txn_id: int,
    x_user_id: Optional[str] = Header(default=None),
) -> dict:
    return handlers.handle_delete_transaction(_resolve_user_id(request, x_user_id), txn_id, userstore)


# ── Static frontend ───────────────────────────────────────────────────────────
FRONTEND_DIR = Path(__file__).resolve().parent.parent / "frontend"


if config.serve_frontend:
    @app.get("/")
    def index() -> FileResponse:
        """Convenience: serves frontend/index.html at /. Set SERVE_FRONTEND=false
        if you deploy the frontend separately (CloudFront+S3, Amplify, ALB)."""
        return FileResponse(FRONTEND_DIR / "index.html")

# ── AWS Lambda Handler ────────────────────────────────────────────────────────
# ── AWS Lambda Handler ────────────────────────────────────────────────────────
if Mangum:
    _mangum_handler = Mangum(app, lifespan="off")

    def handler(event, context):
        records = event.get("Records", [])
        if records and records[0].get("eventSource") == "aws:sqs":
            return handlers.handle_sqs_event(
                event=event,
                storage=storage,
                ai_client=ai_client,
                userstore=userstore,
            )

        if event.get("version") == "2.0":
            event.setdefault("requestContext", {})
            event["requestContext"].setdefault("http", {})
            event["requestContext"]["http"].setdefault("sourceIp", "0.0.0.0")
            event["requestContext"]["http"].setdefault("userAgent", "unknown")

        return _mangum_handler(event, context)
