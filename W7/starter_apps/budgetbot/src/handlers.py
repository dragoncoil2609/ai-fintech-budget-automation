"""Endpoint business logic for BudgetBot."""
import csv
import io
from typing import Optional


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


def handle_upload(
    user_id: str,
    filename: str,
    data: bytes,
    ai_client,
    storage,
    userstore,
) -> dict:
    """Parse CSV → categorize each row via AI → persist to userstore."""
    key = f"{user_id}/{filename}"
    location = storage.put(key, data)
    rows = _parse_csv(data)
    inserted = 0
    samples = []
    for row in rows:
        cat_result = ai_client.categorize(
            description=row["description"], amount=row["amount"], date=row["date"]
        )
        txn = {
            "date": row["date"],
            "description": row["description"],
            "amount": row["amount"],
            "category": cat_result["category"],
            "confidence": cat_result["confidence"],
        }
        userstore.add_transaction(user_id, txn)
        inserted += 1
        if len(samples) < 5:
            samples.append(txn)
    return {
        "filename": filename,
        "stored_at": location,
        "rows_parsed": len(rows),
        "rows_inserted": inserted,
        "sample_categorized": samples,
    }


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
