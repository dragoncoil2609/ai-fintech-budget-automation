"""Smoke tests for DocHub. Verifies multi-tenant isolation works end-to-end."""
import os
import sys
import tempfile
from pathlib import Path

os.environ.setdefault("AI_BACKEND", "local")
os.environ.setdefault("STORAGE_BACKEND", "local")
os.environ.setdefault("USERSTORE_BACKEND", "sqlite")
os.environ.setdefault("VECTOR_BACKEND", "local")
_tmp = tempfile.mkdtemp(prefix="dochub-test-")
os.environ["STORAGE_LOCAL_DIR"] = str(Path(_tmp) / "uploads")
os.environ["USERSTORE_SQLITE_PATH"] = str(Path(_tmp) / "documents.db")

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from fastapi.testclient import TestClient
from src.app import app


client = TestClient(app)


def _headers(tenant: str, user: str = "alice") -> dict:
    return {"X-Tenant-Id": tenant, "X-User-Id": user}


def test_health():
    r = client.get("/health")
    assert r.status_code == 200
    assert r.json()["backends"]["vector"] == "local"


def test_upload_then_query():
    content = b"The termination clause requires 60 days written notice. Penalty is 3 months fees."
    r = client.post(
        "/upload",
        files={"file": ("contract.txt", content, "text/plain")},
        data={"doc_type": "contract"},
        headers=_headers("tenant-acme"),
    )
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["tenant_id"] == "tenant-acme"
    assert body["doc_type"] == "contract"

    r = client.post(
        "/query",
        json={"question": "What is the termination notice period?"},
        headers=_headers("tenant-acme"),
    )
    assert r.status_code == 200
    assert len(r.json()["citations"]) >= 1


def test_tenant_isolation_documents_not_visible_across_tenants():
    """Critical security property: tenant A cannot see tenant B's docs or query results."""
    client.post(
        "/upload",
        files={"file": ("secret_acme.txt", b"ACME confidential salary data: CEO 1B VND.", "text/plain")},
        data={"doc_type": "confidential"},
        headers=_headers("tenant-A"),
    )
    client.post(
        "/upload",
        files={"file": ("secret_globex.txt", b"Globex internal merger plans for Q3.", "text/plain")},
        data={"doc_type": "confidential"},
        headers=_headers("tenant-B"),
    )

    # Tenant A should ONLY see their own docs
    a_docs = client.get("/docs/list", headers=_headers("tenant-A")).json()["docs"]
    a_filenames = {d["filename"] for d in a_docs}
    assert "secret_acme.txt" in a_filenames
    assert "secret_globex.txt" not in a_filenames

    # Tenant A query MUST NOT return Globex's content
    r = client.post(
        "/query",
        json={"question": "What are the merger plans?"},
        headers=_headers("tenant-A"),
    )
    body = r.json()
    cite_texts = " ".join(c["text"] for c in body["citations"])
    assert "merger" not in cite_texts.lower()  # Globex's content must not leak

    # Tenant B can ask about their own data
    r = client.post(
        "/query",
        json={"question": "What are the merger plans?"},
        headers=_headers("tenant-B"),
    )
    body = r.json()
    assert len(body["citations"]) >= 1
    cite_texts = " ".join(c["text"] for c in body["citations"])
    assert "merger" in cite_texts.lower()


def test_filter_by_doc_type():
    client.post(
        "/upload",
        files={"file": ("contract1.txt", b"Contract terms.", "text/plain")},
        data={"doc_type": "contract"},
        headers=_headers("tenant-filter"),
    )
    client.post(
        "/upload",
        files={"file": ("policy1.txt", b"Policy rules.", "text/plain")},
        data={"doc_type": "policy"},
        headers=_headers("tenant-filter"),
    )
    r = client.get("/docs/list?doc_type=contract", headers=_headers("tenant-filter"))
    docs = r.json()["docs"]
    assert all(d["doc_type"] == "contract" for d in docs)
    assert len(docs) == 1
