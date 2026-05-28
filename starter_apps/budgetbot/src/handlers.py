"""Endpoint business logic for BudgetBot."""
import csv
import io
import json
import uuid
import logging
from typing import Optional
from .metrics import put_metric
logger = logging.getLogger(__name__)


def _parse_csv(data: bytes) -> list:
    """Expect CSV columns: date, description, amount. Header row optional."""
    text = data.decode("utf-8-sig", errors="replace")
    reader = csv.reader(io.StringIO(text))
    rows = list(reader)
    if not rows:
        return []
    # Detect header
    header = [c.lower().strip() for c in rows[0]]
    if "date" in header and "amount" in header:
        idx = {col: i for i, col in enumerate(header)}
        data_rows = rows[1:]
    else:
        idx = {"date": 0, "description": 1, "amount": 2}
        data_rows = rows
    parsed = []
    for r in data_rows:
        if len(r) < 3 or not r[idx.get("date", 0)].strip():
            continue
        try:
            parsed.append({
                "date": r[idx.get("date", 0)].strip(),
                "description": r[idx.get("description", 1)].strip(),
                "amount": float(r[idx.get("amount", 2)].strip().replace(",", "")),
            })
        except (ValueError, IndexError):
            continue
    return parsed


def _parse_pdf(data: bytes) -> list:
    """Extract tables from PDF using pdfplumber."""
    try:
        import pdfplumber
    except ImportError:
        raise ImportError("pdfplumber not installed. Add it to requirements.txt")
    import io
    
    parsed = []
    with pdfplumber.open(io.BytesIO(data)) as pdf:
        for page in pdf.pages:
            tables = page.extract_tables()
            for table in tables:
                if not table:
                    continue
                header = None
                idx = {}
                for row in table:
                    if not row or not any(row): continue
                    row = [str(c).replace('\n', ' ').strip() if c else "" for c in row]
                    
                    if header is None:
                        header = [c.lower() for c in row]
                        if "date" in header and "amount" in header:
                            idx = {col: i for i, col in enumerate(header)}
                        else:
                            idx = {"date": 0, "description": 1, "amount": 2}
                            # process as data row if it doesn't look like a header
                            try:
                                amount_str = row[idx.get("amount", 2)].strip().replace(",", "")
                                parsed.append({
                                    "date": row[idx.get("date", 0)].strip(),
                                    "description": row[idx.get("description", 1)].strip(),
                                    "amount": float(amount_str),
                                })
                            except (ValueError, IndexError):
                                pass
                    else:
                        if len(row) < 3 or not row[idx.get("date", 0)].strip():
                            continue
                        try:
                            amount_str = row[idx.get("amount", 2)].strip().replace(",", "")
                            parsed.append({
                                "date": row[idx.get("date", 0)].strip(),
                                "description": row[idx.get("description", 1)].strip(),
                                "amount": float(amount_str),
                            })
                        except (ValueError, IndexError):
                            continue
    return parsed


def _categorize_and_save(
    user_id: str,
    filename: str,
    data: bytes,
    location: str,
    ai_client,
    userstore,
    route: str = "/process",
) -> dict:
    """Parse CSV/PDF → categorize mỗi row bằng AI → lưu vào userstore.
    Dùng chung cho cả upload trực tiếp, xử lý từ S3 và SQS worker.
    """
    if filename.lower().endswith(".pdf"):
        rows = _parse_pdf(data)
    else:
        rows = _parse_csv(data)

    put_metric(
        "RowsParsed",
        len(rows),
        "Count",
        route=route,
        user_id=user_id,
    )

    all_past = userstore.list_transactions(user_id)
    past_transactions = [t for t in all_past if t.get("confidence") == "high"]

    import concurrent.futures

    def process_row(row):
        cat_result = ai_client.categorize(
            description=row["description"],
            amount=row["amount"],
            date=row["date"],
            past_transactions=past_transactions,
        )
        return {
            "date": row["date"],
            "description": row["description"],
            "amount": row["amount"],
            "category": cat_result["category"],
            "confidence": cat_result["confidence"],
        }

    inserted = 0
    samples = []

    # Gọi AI song song cho tất cả các dòng, tối đa 20 luồng cùng lúc.
    with concurrent.futures.ThreadPoolExecutor(max_workers=20) as executor:
        categorized_txns = list(executor.map(process_row, rows))

    # Lưu vào database tuần tự để tránh lỗi connection/thread-safety.
    for txn in categorized_txns:
        userstore.add_transaction(user_id, txn)
        inserted += 1
        if len(samples) < 5:
            samples.append(txn)

    put_metric(
        "RowsInserted",
        inserted,
        "Count",
        route=route,
        user_id=user_id,
    )

    return {
        "filename": filename,
        "stored_at": location,
        "rows_parsed": len(rows),
        "rows_inserted": inserted,
        "sample_categorized": samples,
    }

def handle_upload(
    user_id: str,
    filename: str,
    data: bytes,
    ai_client,
    storage,
    userstore,
) -> dict:
    """Parse CSV/PDF → categorize each row via AI → persist to userstore.
    Đây là luồng upload cũ file đi qua Lambda.
    """
    try:
        put_metric(
            "UploadJobCreated",
            1,
            "Count",
            route="/upload",
            user_id=user_id,
        )

        key = f"{user_id}/{filename}"
        location = storage.put(key, data)

        result = _categorize_and_save(
            user_id=user_id,
            filename=filename,
            data=data,
            location=location,
            ai_client=ai_client,
            userstore=userstore,
            route="/upload",
        )

        put_metric(
            "UploadJobSucceeded",
            1,
            "Count",
            route="/upload",
            user_id=user_id,
        )

        return result

    except Exception:
        put_metric(
            "UploadJobFailed",
            1,
            "Count",
            route="/upload",
            user_id=user_id,
        )
        raise

def handle_process_from_s3(
    user_id: str,
    s3_key: str,
    filename: str,
    storage,
    ai_client,
    userstore,
) -> dict:
    """Đọc file đã upload lên S3 bằng presigned URL → categorize → lưu vào userstore.
    Đây là bước xử lý đồng bộ sau presigned upload.
    """
    try:
        put_metric(
            "ProcessJobStarted",
            1,
            "Count",
            route="/process",
            user_id=user_id,
        )

        data = storage.get(s3_key)
        location = f"s3://{s3_key}"

        result = _categorize_and_save(
            user_id=user_id,
            filename=filename,
            data=data,
            location=location,
            ai_client=ai_client,
            userstore=userstore,
            route="/process",
        )

        put_metric(
            "UploadJobSucceeded",
            1,
            "Count",
            route="/process",
            user_id=user_id,
        )

        return result

    except Exception:
        put_metric(
            "UploadJobFailed",
            1,
            "Count",
            route="/process",
            user_id=user_id,
        )
        raise

def handle_enqueue(
    user_id: str,
    s3_key: str,
    filename: str,
    sqs_queue_url: str,
    userstore,
) -> dict:
    import boto3
    import traceback

    job_id = str(uuid.uuid4())

    print("ENQUEUE_START", {
        "job_id": job_id,
        "user_id": user_id,
        "s3_key": s3_key,
        "filename": filename,
        "sqs_queue_url": sqs_queue_url,
    })

    try:
        print("CREATE_JOB_START")
        userstore.create_job(job_id=job_id, user_id=user_id, s3_key=s3_key, filename=filename)
        print("CREATE_JOB_OK")

        put_metric(
            "UploadJobCreated",
            1,
            "Count",
            route="/enqueue",
            user_id=user_id,
        )

        print("SQS_SEND_START")
        sqs = boto3.client("sqs")
        message = {
            "job_id": job_id,
            "user_id": user_id,
            "s3_key": s3_key,
            "filename": filename,
        }
        resp = sqs.send_message(
            QueueUrl=sqs_queue_url,
            MessageBody=json.dumps(message),
        )
        print("SQS_SEND_OK", resp)

        put_metric(
            "SQSMessageSent",
            1,
            "Count",
            route="/enqueue",
            user_id=user_id,
        )

        return {
            "job_id": job_id,
            "status": "QUEUED",
            "message": "File đã được đưa vào hàng đợi xử lý",
        }

    except Exception as exc:
        put_metric(
            "UploadJobFailed",
            1,
            "Count",
            route="/enqueue",
            user_id=user_id,
        )
        print("ENQUEUE_ERROR:", repr(exc))
        traceback.print_exc()
        raise


def handle_job_status(job_id: str, userstore) -> dict:
    """Trả về trạng thái của job theo job_id."""
    job = userstore.get_job(job_id)
    if not job:
        return {"job_id": job_id, "status": "NOT_FOUND"}
    return job


def handle_sqs_event(event: dict, storage, ai_client, userstore) -> dict:
    """Xử lý SQS event — được trigger bởi SQS khi có message mới.
    Đọc file từ S3, parse CSV/PDF, gọi Bedrock, lưu RDS, cập nhật job status.
    """
    results = []

    for record in event.get("Records", []):
        message = {}

        try:
            message = json.loads(record["body"])
            job_id = message["job_id"]
            user_id = message["user_id"]
            s3_key = message["s3_key"]
            filename = message["filename"]

            logger.info({"event": "sqs_job_start", "job_id": job_id, "s3_key": s3_key})

            put_metric(
                "SQSMessageReceived",
                1,
                "Count",
                route="sqs_worker",
                user_id=user_id,
            )

            userstore.update_job_status(job_id, "PROCESSING")

            data = storage.get(s3_key)
            location = f"s3://{s3_key}"

            result = _categorize_and_save(
                user_id=user_id,
                filename=filename,
                data=data,
                location=location,
                ai_client=ai_client,
                userstore=userstore,
                route="sqs_worker",
            )

            userstore.update_job_status(job_id, "COMPLETED", rows_inserted=result["rows_inserted"])

            put_metric(
                "SQSMessageProcessed",
                1,
                "Count",
                route="sqs_worker",
                user_id=user_id,
            )

            put_metric(
                "UploadJobSucceeded",
                1,
                "Count",
                route="sqs_worker",
                user_id=user_id,
            )

            logger.info({"event": "sqs_job_done", "job_id": job_id, "rows": result["rows_inserted"]})
            results.append({"job_id": job_id, "status": "COMPLETED"})

        except Exception as exc:
            job_id = message.get("job_id", "unknown")
            user_id = message.get("user_id", "unknown")

            put_metric(
                "SQSMessageFailed",
                1,
                "Count",
                route="sqs_worker",
                user_id=user_id,
            )

            put_metric(
                "UploadJobFailed",
                1,
                "Count",
                route="sqs_worker",
                user_id=user_id,
            )

            logger.exception({"event": "sqs_job_failed", "job_id": job_id, "error": str(exc)})

            try:
                userstore.update_job_status(job_id, "FAILED", error=str(exc))
            except Exception:
                pass

            raise  # Re-raise để SQS retry

    return {"processed": len(results)}



def handle_summary(user_id: str, month: Optional[str], userstore) -> dict:
    summary = userstore.summary(user_id, month=month)
    total = sum(v["total"] for v in summary.values())
    sorted_cats = sorted(summary.items(), key=lambda kv: -abs(kv[1]["total"]))
    return {
        "user_id": user_id,
        "month": month,
        "total_spend": total,
        "by_category": dict(sorted_cats),
        "top_3_drivers": [
            {"category": cat, "total": v["total"], "count": v["count"]}
            for cat, v in sorted_cats[:3]
        ],
    }


def handle_list_transactions(user_id: str, month: Optional[str], userstore) -> dict:
    return {"user_id": user_id, "month": month, "transactions": userstore.list_transactions(user_id, month=month)}


def handle_update_category(user_id: str, txn_id: int, new_category: str, userstore) -> dict:
    userstore.update_category(user_id, txn_id, new_category)
    return {"status": "success"}

def handle_clear_transactions(user_id: str, userstore) -> dict:
    userstore.clear_transactions(user_id)
    return {"status": "success"}

def handle_chat(user_id: str, message: str, userstore, chatbot_client) -> dict:
    transactions = userstore.list_transactions(user_id)
    budgets = userstore.get_budgets(user_id)
    reply = chatbot_client.chat(user_id, message, transactions, budgets, userstore)
    return {"reply": reply}

def handle_get_budgets(user_id: str, userstore) -> dict:
    budgets = userstore.get_budgets(user_id)
    summary = userstore.summary(user_id)
    
    alerts = []
    for category, limit in budgets.items():
        spent = summary.get(category, {}).get("total", 0)
        if spent > limit:
            alerts.append({"category": category, "limit": limit, "spent": spent})
            
    return {"budgets": budgets, "alerts": alerts}