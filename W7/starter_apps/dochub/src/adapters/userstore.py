"""Document metadata stores. Schema includes tenant_id for multi-tenant isolation.

Interface:
    add_doc(tenant_id, doc_id, metadata) -> None
    list_docs(tenant_id, doc_type=None) -> list[dict]
    get_doc(tenant_id, doc_id) -> dict | None
"""
import json
from datetime import datetime, timezone
from pathlib import Path


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


class DynamoDBUserStore:
    """PK=tenant_id, SK=DOC#<doc_id>. Single-table multi-tenant pattern."""

    def __init__(self, table_name: str, region: str):
        import boto3
        if not table_name:
            raise ValueError("USERSTORE_TABLE must be set for DynamoDB backend")
        self.table = boto3.resource("dynamodb", region_name=region).Table(table_name)

    def add_doc(self, tenant_id: str, doc_id: str, metadata: dict) -> None:
        self.table.put_item(Item={
            "tenant_id": tenant_id,
            "sk": f"DOC#{doc_id}",
            "doc_id": doc_id,
            "created_at": _now(),
            **metadata,
        })

    def list_docs(self, tenant_id: str, doc_type: str | None = None) -> list:
        kwargs = {
            "KeyConditionExpression": "tenant_id = :t AND begins_with(sk, :p)",
            "ExpressionAttributeValues": {":t": tenant_id, ":p": "DOC#"},
        }
        if doc_type:
            kwargs["FilterExpression"] = "doc_type = :dt"
            kwargs["ExpressionAttributeValues"][":dt"] = doc_type
        return self.table.query(**kwargs).get("Items", [])

    def get_doc(self, tenant_id: str, doc_id: str) -> dict | None:
        resp = self.table.get_item(Key={"tenant_id": tenant_id, "sk": f"DOC#{doc_id}"})
        return resp.get("Item")


class PostgresUserStore:
    def __init__(self, url: str):
        try:
            import psycopg2
        except ImportError:
            raise ImportError("psycopg2 not installed. Run: pip install psycopg2-binary")
        if not url:
            raise ValueError("USERSTORE_POSTGRES_URL must be set")
        self.conn = psycopg2.connect(url)
        self.conn.autocommit = True
        self._init_schema()

    def _init_schema(self):
        with self.conn.cursor() as cur:
            cur.execute("""
                CREATE TABLE IF NOT EXISTS documents (
                    tenant_id TEXT NOT NULL,
                    doc_id TEXT NOT NULL,
                    doc_type TEXT,
                    uploaded_by TEXT,
                    metadata JSONB,
                    created_at TIMESTAMPTZ DEFAULT NOW(),
                    PRIMARY KEY (tenant_id, doc_id)
                );
                CREATE INDEX IF NOT EXISTS doc_tenant_type_idx ON documents(tenant_id, doc_type);
                CREATE INDEX IF NOT EXISTS doc_tenant_created_idx ON documents(tenant_id, created_at DESC);
            """)

    def add_doc(self, tenant_id, doc_id, metadata):
        with self.conn.cursor() as cur:
            cur.execute(
                "INSERT INTO documents (tenant_id, doc_id, doc_type, uploaded_by, metadata) "
                "VALUES (%s, %s, %s, %s, %s) "
                "ON CONFLICT (tenant_id, doc_id) DO UPDATE SET metadata = EXCLUDED.metadata",
                (
                    tenant_id, doc_id,
                    metadata.get("doc_type"),
                    metadata.get("uploaded_by"),
                    json.dumps(metadata),
                ),
            )

    def list_docs(self, tenant_id, doc_type=None):
        sql = "SELECT doc_id, doc_type, uploaded_by, metadata, created_at FROM documents WHERE tenant_id = %s"
        params: list = [tenant_id]
        if doc_type:
            sql += " AND doc_type = %s"
            params.append(doc_type)
        sql += " ORDER BY created_at DESC"
        with self.conn.cursor() as cur:
            cur.execute(sql, params)
            return [
                {"doc_id": r[0], "doc_type": r[1], "uploaded_by": r[2], **(r[3] or {}), "created_at": r[4].isoformat()}
                for r in cur.fetchall()
            ]

    def get_doc(self, tenant_id, doc_id):
        with self.conn.cursor() as cur:
            cur.execute(
                "SELECT doc_type, uploaded_by, metadata, created_at FROM documents "
                "WHERE tenant_id = %s AND doc_id = %s",
                (tenant_id, doc_id),
            )
            r = cur.fetchone()
            if not r:
                return None
            return {"doc_id": doc_id, "doc_type": r[0], "uploaded_by": r[1], **(r[2] or {}), "created_at": r[3].isoformat()}


class SQLiteUserStore:
    def __init__(self, db_path: str):
        import sqlite3
        Path(db_path).parent.mkdir(parents=True, exist_ok=True)
        self.conn = sqlite3.connect(db_path, check_same_thread=False)
        self._init_schema()

    def _init_schema(self):
        self.conn.executescript("""
            CREATE TABLE IF NOT EXISTS documents (
                tenant_id TEXT NOT NULL,
                doc_id TEXT NOT NULL,
                doc_type TEXT,
                uploaded_by TEXT,
                metadata TEXT,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                PRIMARY KEY (tenant_id, doc_id)
            );
            CREATE INDEX IF NOT EXISTS doc_tenant_type_idx ON documents(tenant_id, doc_type);
            CREATE INDEX IF NOT EXISTS doc_tenant_created_idx ON documents(tenant_id, created_at DESC);
        """)
        self.conn.commit()

    def add_doc(self, tenant_id, doc_id, metadata):
        self.conn.execute(
            "INSERT OR REPLACE INTO documents (tenant_id, doc_id, doc_type, uploaded_by, metadata) "
            "VALUES (?, ?, ?, ?, ?)",
            (
                tenant_id, doc_id,
                metadata.get("doc_type"),
                metadata.get("uploaded_by"),
                json.dumps(metadata),
            ),
        )
        self.conn.commit()

    def list_docs(self, tenant_id, doc_type=None):
        if doc_type:
            cur = self.conn.execute(
                "SELECT doc_id, doc_type, uploaded_by, metadata, created_at FROM documents "
                "WHERE tenant_id = ? AND doc_type = ? ORDER BY created_at DESC",
                (tenant_id, doc_type),
            )
        else:
            cur = self.conn.execute(
                "SELECT doc_id, doc_type, uploaded_by, metadata, created_at FROM documents "
                "WHERE tenant_id = ? ORDER BY created_at DESC",
                (tenant_id,),
            )
        return [
            {
                "doc_id": r[0], "doc_type": r[1], "uploaded_by": r[2],
                **(json.loads(r[3]) if r[3] else {}),
                "created_at": r[4],
            }
            for r in cur.fetchall()
        ]

    def get_doc(self, tenant_id, doc_id):
        cur = self.conn.execute(
            "SELECT doc_type, uploaded_by, metadata, created_at FROM documents "
            "WHERE tenant_id = ? AND doc_id = ?",
            (tenant_id, doc_id),
        )
        r = cur.fetchone()
        if not r:
            return None
        return {
            "doc_id": doc_id, "doc_type": r[0], "uploaded_by": r[1],
            **(json.loads(r[2]) if r[2] else {}),
            "created_at": r[3],
        }


class DocumentDBUserStore:
    """Multi-tenant MongoDB-compatible store. PK shard on tenant_id for scaling."""

    def __init__(self, url: str, db_name: str = "dochub", tls_ca_file: str = ""):
        try:
            from pymongo import MongoClient
        except ImportError:
            raise ImportError("pymongo not installed. Run: pip install -r requirements-optional.txt")
        if not url:
            raise ValueError("USERSTORE_MONGO_URL must be set")
        kwargs: dict = {}
        if "documentdb" in url.lower() or tls_ca_file:
            kwargs["tls"] = True
        if tls_ca_file:
            kwargs["tlsCAFile"] = tls_ca_file
        self.client = MongoClient(url, **kwargs)
        self.col = self.client[db_name]["documents"]
        self.col.create_index([("tenant_id", 1), ("doc_id", 1)], unique=True)
        self.col.create_index([("tenant_id", 1), ("doc_type", 1)])
        self.col.create_index([("tenant_id", 1), ("created_at", -1)])

    def add_doc(self, tenant_id, doc_id, metadata):
        self.col.update_one(
            {"tenant_id": tenant_id, "doc_id": doc_id},
            {"$set": {**metadata, "tenant_id": tenant_id, "doc_id": doc_id, "created_at": _now()}},
            upsert=True,
        )

    def list_docs(self, tenant_id, doc_type=None):
        q: dict = {"tenant_id": tenant_id}
        if doc_type:
            q["doc_type"] = doc_type
        return [
            {**{k: v for k, v in d.items() if k != "_id"}}
            for d in self.col.find(q).sort("created_at", -1)
        ]

    def get_doc(self, tenant_id, doc_id):
        d = self.col.find_one({"tenant_id": tenant_id, "doc_id": doc_id})
        if not d:
            return None
        return {k: v for k, v in d.items() if k != "_id"}


class MySQLUserStore:
    """RDS MySQL / Aurora MySQL adapter. Multi-tenant: PK = (tenant_id, doc_id)."""

    def __init__(self, url: str):
        try:
            import pymysql
            from urllib.parse import urlparse
        except ImportError:
            raise ImportError("pymysql not installed. Run: pip install -r requirements-optional.txt")
        if not url:
            raise ValueError("USERSTORE_MYSQL_URL must be set")
        p = urlparse(url)
        self.conn = pymysql.connect(
            host=p.hostname, port=p.port or 3306,
            user=p.username, password=p.password,
            database=p.path.lstrip("/"),
            charset="utf8mb4", autocommit=True,
        )
        self._init_schema()

    def _init_schema(self):
        with self.conn.cursor() as cur:
            cur.execute("""
                CREATE TABLE IF NOT EXISTS documents (
                    tenant_id VARCHAR(255) NOT NULL,
                    doc_id VARCHAR(255) NOT NULL,
                    doc_type VARCHAR(64),
                    uploaded_by VARCHAR(255),
                    metadata JSON,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    PRIMARY KEY (tenant_id, doc_id),
                    INDEX idx_tenant_type (tenant_id, doc_type),
                    INDEX idx_tenant_created (tenant_id, created_at)
                ) CHARACTER SET utf8mb4
            """)

    def add_doc(self, tenant_id, doc_id, metadata):
        with self.conn.cursor() as cur:
            cur.execute(
                "REPLACE INTO documents (tenant_id, doc_id, doc_type, uploaded_by, metadata) "
                "VALUES (%s, %s, %s, %s, %s)",
                (tenant_id, doc_id, metadata.get("doc_type"), metadata.get("uploaded_by"),
                 json.dumps(metadata)),
            )

    def list_docs(self, tenant_id, doc_type=None):
        if doc_type:
            sql = ("SELECT doc_id, doc_type, uploaded_by, metadata, created_at FROM documents "
                   "WHERE tenant_id = %s AND doc_type = %s ORDER BY created_at DESC")
            params = (tenant_id, doc_type)
        else:
            sql = ("SELECT doc_id, doc_type, uploaded_by, metadata, created_at FROM documents "
                   "WHERE tenant_id = %s ORDER BY created_at DESC")
            params = (tenant_id,)
        with self.conn.cursor() as cur:
            cur.execute(sql, params)
            return [
                {"doc_id": r[0], "doc_type": r[1], "uploaded_by": r[2],
                 **(json.loads(r[3]) if r[3] else {}),
                 "created_at": str(r[4])}
                for r in cur.fetchall()
            ]

    def get_doc(self, tenant_id, doc_id):
        with self.conn.cursor() as cur:
            cur.execute(
                "SELECT doc_type, uploaded_by, metadata, created_at FROM documents "
                "WHERE tenant_id = %s AND doc_id = %s",
                (tenant_id, doc_id),
            )
            r = cur.fetchone()
            if not r:
                return None
            return {"doc_id": doc_id, "doc_type": r[0], "uploaded_by": r[1],
                    **(json.loads(r[2]) if r[2] else {}),
                    "created_at": str(r[3])}
