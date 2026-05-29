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
import src.app as app_module
from src.app import app, userstore


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


def test_chat_memory_recent_messages_are_isolated_per_user():
    userstore.get_or_create_chat_session("chat-user-a", "session-a")
    userstore.add_chat_message("chat-user-a", "session-a", "user", "Tôi muốn tiết kiệm 5 triệu mỗi tháng")
    userstore.add_chat_message("chat-user-a", "session-a", "assistant", "Mình sẽ ghi nhớ mục tiêu đó.")

    userstore.get_or_create_chat_session("chat-user-b", "session-b")
    userstore.add_chat_message("chat-user-b", "session-b", "user", "Tôi muốn giảm ăn ngoài")

    recent_a = userstore.list_recent_chat_messages("chat-user-a", "session-a", limit=8)
    recent_b = userstore.list_recent_chat_messages("chat-user-b", "session-b", limit=8)

    assert [m["role"] for m in recent_a] == ["user", "assistant"]
    assert "5 triệu" in recent_a[0]["text"]
    assert len(recent_b) == 1
    assert "ăn ngoài" in recent_b[0]["text"]


def test_chat_endpoint_persists_server_side_memory(monkeypatch):
    class FakeChatbot:
        def chat(self, **kwargs):
            assert kwargs["messages_context"][-1]["text"] == "Nhớ giúp tôi mục tiêu tiết kiệm"
            yield "Đã ghi nhớ mục tiêu của bạn."

        def summarize_memory(self, existing_summary, messages):
            return existing_summary

    monkeypatch.setattr(app_module, "chatbot_client", FakeChatbot())

    r = client.post(
        "/chat",
        json={"message": "Nhớ giúp tôi mục tiêu tiết kiệm", "session_id": "local-session"},
        headers={"X-User-Id": "memory-user"},
    )

    assert r.status_code == 200, r.text
    assert "Đã ghi nhớ" in r.text

    recent = userstore.list_recent_chat_messages("memory-user", "memory-user:local-session", limit=8)
    assert [m["role"] for m in recent] == ["user", "assistant"]
    assert "mục tiêu tiết kiệm" in recent[0]["text"]
