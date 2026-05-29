"""Endpoint business logic for BudgetBot."""
import csv
import io
import json
import uuid
import logging
import re
from typing import Optional
from .metrics import put_metric
logger = logging.getLogger(__name__)


CHAT_RECENT_MESSAGE_LIMIT = 8
CHAT_SUMMARY_KEEP_RECENT = 8
CHAT_SUMMARY_BATCH_LIMIT = 20
CHAT_TRANSACTION_LIMIT = 40

_CATEGORY_HINTS = {
    "Food": ["food", "eat", "eating", "restaurant", "coffee", "cafe", "ăn", "an", "uống", "uong"],
    "Transport": ["transport", "grab", "taxi", "fuel", "di chuyển", "di chuyen", "xe"],
    "Shopping": ["shopping", "shop", "mua sắm", "mua sam"],
    "Utilities": ["utilities", "electric", "water", "internet", "tiện ích", "tien ich"],
    "Entertainment": ["entertainment", "game", "cinema", "giải trí", "giai tri"],
    "Health": ["health", "pharmacy", "hospital", "sức khỏe", "suc khoe"],
    "Subscriptions": ["subscription", "subscriptions", "netflix", "spotify", "đăng ký", "dang ky"],
    "Income": ["income", "salary", "thu nhập", "thu nhap", "lương", "luong"],
    "Transfer": ["transfer", "chuyển khoản", "chuyen khoan"],
    "Other": ["other", "khác", "khac"],
}


def _normalize_chat_session_id(user_id: str, session_id: str | None) -> str | None:
    if not session_id:
        return None
    safe_session = re.sub(r"[^a-zA-Z0-9_.:-]", "-", session_id.strip())[:120]
    safe_user = re.sub(r"[^a-zA-Z0-9_.:-]", "-", user_id.strip())[:80]
    if not safe_session:
        return None
    return f"{safe_user}:{safe_session}"


def _select_chat_transactions(message: str, transactions: list, limit: int = CHAT_TRANSACTION_LIMIT) -> list:
    if len(transactions) <= limit:
        return transactions

    message_l = message.lower()
    hinted_categories = [
        category
        for category, hints in _CATEGORY_HINTS.items()
        if any(hint in message_l for hint in hints)
    ]
    if hinted_categories:
        filtered = [t for t in transactions if t.get("category") in hinted_categories]
        if filtered:
            return filtered[:limit]

    return transactions[:limit]


def _parse_csv(data: bytes, mapping: dict = None) -> list:
    """Expect CSV columns. Header row optional. If mapping is provided, use it."""
    text = data.decode("utf-8-sig", errors="replace")
    reader = csv.reader(io.StringIO(text))
    rows = list(reader)
    if not rows:
        return []
    
    # Detect header or use mapping
    data_rows = rows
    if mapping:
        idx = {k: int(v) for k, v in mapping.items()}
    else:
        header = [c.lower().strip() for c in rows[0]]
        if "date" in header and "amount" in header:
            idx = {col: i for i, col in enumerate(header)}
            data_rows = rows[1:]
        else:
            idx = {"date": 0, "description": 1, "amount": 2}

    parsed = []
    for r in data_rows:
        if len(r) <= max(idx.values()) or not r[idx.get("date", 0)].strip():
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
    mapping: dict = None,
) -> dict:
    """Parse CSV/PDF → categorize mỗi row bằng AI → lưu vào userstore.
    Dùng chung cho cả upload trực tiếp, xử lý từ S3 và SQS worker.
    """
    if filename.lower().endswith(".pdf"):
        rows = _parse_pdf(data)
    else:
        rows = _parse_csv(data, mapping=mapping)

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

    # Gọi AI song song cho tất cả các dòng, tối đa 5 luồng cùng lúc để tránh rate limit của AWS Bedrock.
    with concurrent.futures.ThreadPoolExecutor(max_workers=5) as executor:
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
    mapping: dict = None,
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
            mapping=mapping,
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
    mapping: dict = None,
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
            "mapping": mapping,
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
            mapping = message.get("mapping")

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
                mapping=mapping,
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
    
    # Filter out positive amounts for top drivers (only consider expenses)
    expenses = {k: v for k, v in summary.items() if v["total"] < 0}
    sorted_cats = sorted(expenses.items(), key=lambda kv: kv[1]["total"])
    
    # Calculate daily trends
    from collections import defaultdict
    txns = userstore.list_transactions(user_id, month=month)
    daily_agg = defaultdict(float)
    for t in txns:
        if float(t["amount"]) < 0:
            daily_agg[t["date"][:10]] += abs(float(t["amount"]))
    
    daily_trends = [{"date": k, "amount": v} for k, v in sorted(daily_agg.items())]

    return {
        "user_id": user_id,
        "month": month,
        "total_spend": total,
        "by_category": summary,
        "top_3_drivers": [
            {"category": cat, "total": v["total"], "count": v["count"]}
            for cat, v in sorted_cats[:3]
        ],
        "daily_trends": daily_trends,
    }


def handle_list_transactions(user_id: str, month: Optional[str], userstore) -> dict:
    return {"user_id": user_id, "month": month, "transactions": userstore.list_transactions(user_id, month=month)}


def handle_update_category(user_id: str, txn_id: int, new_category: str, userstore) -> dict:
    userstore.update_category(user_id, txn_id, new_category)
    return {"status": "success"}

def handle_clear_transactions(user_id: str, userstore) -> dict:
    userstore.clear_transactions(user_id)
    if hasattr(userstore, "clear_chat_memory"):
        userstore.clear_chat_memory(user_id)
    return {"status": "success"}

def handle_delete_transaction(user_id: str, txn_id: int, userstore) -> dict:
    userstore.delete_transaction(user_id, txn_id)
    return {"status": "success"}

def handle_set_budget(user_id: str, category: str, amount: float, userstore) -> dict:
    userstore.set_budget(user_id, category, amount)
    return {"status": "success"}

def handle_add_transaction(user_id: str, data: dict, userstore, ai_client) -> dict:
    import uuid
    txn = {
        "date": data.get("date"),
        "description": data.get("description"),
        "amount": data.get("amount"),
        "category": data.get("category", "Other"),
        "confidence": "high", # manual entry -> high confidence
    }
    userstore.add_transaction(user_id, txn)
    return {"status": "success"}


def _chat_memory_available(userstore) -> bool:
    required = [
        "get_or_create_chat_session",
        "add_chat_message",
        "list_recent_chat_messages",
        "list_chat_messages_for_summary",
        "update_chat_summary",
    ]
    return all(hasattr(userstore, name) for name in required)


def handle_chat(user_id: str, message: str, session_id: str | None, month: str | None, userstore, chatbot_client):
    all_transactions = userstore.list_transactions(user_id, month=month)
    has_transactions = bool(all_transactions)
    has_any_transactions = has_transactions or (bool(userstore.list_transactions(user_id)) if month else False)
    if not has_any_transactions and hasattr(userstore, "clear_chat_memory"):
        userstore.clear_chat_memory(user_id)

    transactions = _select_chat_transactions(message, all_transactions)
    budgets = userstore.get_budgets(user_id)
    summary = userstore.summary(user_id, month=month)

    session = {"id": session_id, "summary": "", "profile": {}, "message_count": 0}
    recent_messages = [{"role": "user", "text": message}]

    if _chat_memory_available(userstore):
        server_session_id = _normalize_chat_session_id(user_id, session_id)
        session = userstore.get_or_create_chat_session(user_id, server_session_id)
        userstore.add_chat_message(user_id, session["id"], "user", message)
        session = userstore.get_or_create_chat_session(user_id, session["id"])
        if has_transactions:
            recent_messages = userstore.list_recent_chat_messages(
                user_id,
                session["id"],
                limit=CHAT_RECENT_MESSAGE_LIMIT,
            )
    
    stream_generator = chatbot_client.chat(
        user_id=user_id,
        messages_context=recent_messages,
        transactions=transactions,
        budgets=budgets,
        summary=summary,
        data_scope=f"Month {month}" if month else "All available transactions",
        memory_summary=session.get("summary", "") if has_transactions else "",
        profile=session.get("profile", {}) if has_transactions else {},
        userstore=userstore,
    )
    
    def sse_generator():
        assistant_chunks = []
        for chunk in stream_generator:
            assistant_chunks.append(chunk)
            # SSE format: data: <content>\n\n
            # Ensure newlines in chunk are properly handled if necessary, 
            # though usually just passing the string is fine.
            # Replace newlines in chunk with a placeholder or just send JSON to be safe.
            import json
            yield f"data: {json.dumps({'text': chunk}, ensure_ascii=False)}\n\n"

        assistant_text = "".join(assistant_chunks).strip()
        if assistant_text and _chat_memory_available(userstore):
            userstore.add_chat_message(user_id, session["id"], "assistant", assistant_text)
            messages_to_compact = userstore.list_chat_messages_for_summary(
                user_id,
                session["id"],
                keep_recent=CHAT_SUMMARY_KEEP_RECENT,
                limit=CHAT_SUMMARY_BATCH_LIMIT,
            )
            if messages_to_compact:
                try:
                    updated_summary = chatbot_client.summarize_memory(session.get("summary", ""), messages_to_compact)
                    max_message_id = max(m["id"] for m in messages_to_compact)
                    userstore.update_chat_summary(user_id, session["id"], updated_summary, max_message_id)
                except Exception:
                    logger.exception({"event": "chat_memory_summary_failed", "user_id": user_id, "session_id": session["id"]})
            
    return sse_generator()

def handle_get_budgets(user_id: str, userstore) -> dict:
    budgets = userstore.get_budgets(user_id)
    summary = userstore.summary(user_id)
    
    alerts = []
    for category, limit in budgets.items():
        spent = summary.get(category, {}).get("total", 0)
        if spent > limit:
            alerts.append({"category": category, "limit": limit, "spent": spent})
            
    return {"budgets": budgets, "alerts": alerts}
