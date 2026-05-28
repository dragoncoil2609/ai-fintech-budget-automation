"""FastAPI app for BudgetBot. Runtime-agnostic."""
from pathlib import Path
from typing import Optional

import boto3
import uuid

from fastapi import FastAPI, File, Header, HTTPException, UploadFile
from fastapi.responses import FileResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from .config import config
from .adapters import factory
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


def _resolve_user_id(x_user_id: Optional[str]) -> str:
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
    file: UploadFile = File(...),
    x_user_id: Optional[str] = Header(default=None),
) -> dict:
    """Luồng upload cũ: file đi qua Lambda (multipart). Giữ nguyên cho local dev / fallback."""
    user_id = _resolve_user_id(x_user_id)
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
    body: UploadRequestBody,
    x_user_id: Optional[str] = Header(default=None),
) -> dict:
    """Bước 1 của luồng Presigned URL:
    Lambda tạo presigned PUT URL + s3_key và trả về cho frontend.
    Frontend dùng URL đó để PUT file trực tiếp lên S3 (không qua Lambda).

    Nếu storage backend không hỗ trợ presigned URL (ví dụ local dev),
    trả về upload_url=null để frontend fallback về /upload.
    """
    user_id = _resolve_user_id(x_user_id)
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


@app.post("/process")
def process(
    body: ProcessBody,
    x_user_id: Optional[str] = Header(default=None),
) -> dict:
    """Bước 3 của luồng Presigned URL:
    Frontend đã upload file lên S3 thành công → gọi endpoint này để Lambda đọc
    file từ S3 bằng s3_key, rồi phân loại giao dịch bằng AI và lưu vào DB.
    Lambda không nhận payload file — chỉ nhận s3_key (chuỗi nhỏ).
    """
    user_id = _resolve_user_id(x_user_id)

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
        )
    except Exception as exc:
        # handle_process_from_s3 cũng đã emit UploadJobFailed.
        # Ở đây chỉ chuyển lỗi thành HTTP 500 cho frontend.
        raise HTTPException(status_code=500, detail=f"Lỗi xử lý file từ S3: {exc}") from exc

class EnqueueBody(BaseModel):
    s3_key: str
    filename: str


@app.post("/enqueue")
def enqueue(
    body: EnqueueBody,
    x_user_id: Optional[str] = Header(default=None),
) -> dict:
    """Luồng SQS async:
    Frontend đã PUT file lên S3 → gọi endpoint này để Lambda tạo job_id,
    gửi message vào SQS và trả về job_id ngay. Không cần chờ xử lý AI/RDS.
    """
    user_id = _resolve_user_id(x_user_id)

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


# ── Transactions & Summary ────────────────────────────────────────────────────

@app.get("/summary")
def summary(
    month: Optional[str] = None,
    x_user_id: Optional[str] = Header(default=None),
) -> dict:
    """`month` format: YYYY-MM. Omit for all-time summary."""
    return handlers.handle_summary(_resolve_user_id(x_user_id), month, userstore)


@app.get("/transactions")
def transactions(
    month: Optional[str] = None,
    x_user_id: Optional[str] = Header(default=None),
) -> dict:
    return handlers.handle_list_transactions(_resolve_user_id(x_user_id), month, userstore)


class CategoryUpdate(BaseModel):
    category: str


@app.patch("/transactions/{txn_id}")
def update_category(
    txn_id: int,
    data: CategoryUpdate,
    x_user_id: Optional[str] = Header(default=None),
) -> dict:
    return handlers.handle_update_category(_resolve_user_id(x_user_id), txn_id, data.category, userstore)


@app.delete("/transactions")
def clear_transactions(
    x_user_id: Optional[str] = Header(default=None),
) -> dict:
    return handlers.handle_clear_transactions(_resolve_user_id(x_user_id), userstore)


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