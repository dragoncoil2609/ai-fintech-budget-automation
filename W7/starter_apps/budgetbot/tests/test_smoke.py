"""Smoke tests for BudgetBot in LOCAL_MODE."""
import os
import sys
import tempfile
from pathlib import Path

os.environ.setdefault("AI_BACKEND", "local")
os.environ.setdefault("STORAGE_BACKEND", "local")
os.environ.setdefault("USERSTORE_BACKEND", "sqlite")
_tmp = tempfile.mkdtemp(prefix="budgetbot-test-")
os.environ["STORAGE_LOCAL_DIR"] = str(Path(_tmp) / "uploads")
os.environ["USERSTORE_SQLITE_PATH"] = str(Path(_tmp) / "transactions.db")

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from fastapi.testclient import TestClient
from src.app import app


client = TestClient(app)


SAMPLE_CSV = b"""date,description,amount
2026-05-02,Highlands Coffee,-65000
2026-05-04,Salary deposit,18500000
2026-05-05,Netflix monthly subscription,-260000
2026-05-08,Vincom shopping,-450000
"""


def test_health():
    r = client.get("/health")
    assert r.status_code == 200
    assert r.json()["backends"]["ai"] == "local"


def test_upload_csv_categorizes():
    r = client.post(
        "/upload",
        files={"file": ("statement.csv", SAMPLE_CSV, "text/csv")},
        headers={"X-User-Id": "alice"},
    )
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["rows_parsed"] == 4
    assert body["rows_inserted"] == 4
    cats = [t["category"] for t in body["sample_categorized"]]
    assert "Food" in cats          # Highlands Coffee
    assert "Income" in cats        # Salary deposit
    assert "Subscriptions" in cats # Netflix


def test_summary_aggregates_per_category():
    # Fresh user, fresh data
    client.post(
        "/upload",
        files={"file": ("s.csv", SAMPLE_CSV, "text/csv")},
        headers={"X-User-Id": "bob"},
    )
    r = client.get("/summary", headers={"X-User-Id": "bob"})
    assert r.status_code == 200
    body = r.json()
    assert "by_category" in body
    assert "Food" in body["by_category"]
    assert body["by_category"]["Food"]["count"] >= 1
    # Top drivers sorted by absolute amount
    assert len(body["top_3_drivers"]) <= 3


def test_summary_with_month_filter():
    client.post(
        "/upload",
        files={"file": ("s.csv", SAMPLE_CSV, "text/csv")},
        headers={"X-User-Id": "carol"},
    )
    r = client.get("/summary?month=2026-05", headers={"X-User-Id": "carol"})
    assert r.status_code == 200
    body = r.json()
    assert body["month"] == "2026-05"
    assert body["by_category"]


def test_transactions_isolated_per_user():
    client.post(
        "/upload",
        files={"file": ("s.csv", SAMPLE_CSV, "text/csv")},
        headers={"X-User-Id": "user-iso-A"},
    )
    r_a = client.get("/transactions", headers={"X-User-Id": "user-iso-A"})
    r_b = client.get("/transactions", headers={"X-User-Id": "user-iso-B"})
    assert len(r_a.json()["transactions"]) == 4
    assert len(r_b.json()["transactions"]) == 0
