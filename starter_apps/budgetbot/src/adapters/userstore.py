"""Transaction store adapters.

Interface:
    add_transaction(user_id, txn) -> None       # txn = {date, description, amount, category, confidence}
    list_transactions(user_id, month=None) -> list[dict]
    summary(user_id, month=None) -> {category: {"total": float, "count": int}}
"""
import json
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


class DynamoDBUserStore:
    """PK=user_id, SK=TXN#<date>#<id>. Aggregations require Scan or GSI — accept the trade-off."""

    def __init__(self, table_name: str, region: str):
        import boto3
        if not table_name:
            raise ValueError("USERSTORE_TABLE must be set for DynamoDB backend")
        self.table = boto3.resource("dynamodb", region_name=region).Table(table_name)

    def add_transaction(self, user_id: str, txn: dict) -> None:
        import uuid
        from decimal import Decimal
        sk = f"TXN#{txn['date']}#{uuid.uuid4().hex[:8]}"
        # DynamoDB doesn't accept floats; use Decimal
        item = {**txn, "amount": Decimal(str(txn["amount"]))} if "amount" in txn else txn
        self.table.put_item(Item={"user_id": user_id, "sk": sk, "created_at": _now(), **item})

    def list_transactions(self, user_id: str, month: str | None = None) -> list:
        kwargs = {
            "KeyConditionExpression": "user_id = :u AND begins_with(sk, :p)",
            "ExpressionAttributeValues": {":u": user_id, ":p": f"TXN#{month}" if month else "TXN#"},
        }
        resp = self.table.query(**kwargs)
        return [_decimal_to_float(item) for item in resp.get("Items", [])]

    def summary(self, user_id: str, month: str | None = None) -> dict:
        return _aggregate(self.list_transactions(user_id, month))


def _decimal_to_float(item: dict) -> dict:
    from decimal import Decimal
    return {k: (float(v) if isinstance(v, Decimal) else v) for k, v in item.items()}


class PostgresUserStore:
    def __init__(self, url: str):
        try:
            import psycopg2
        except ImportError:
            raise ImportError("psycopg2 not installed. Run: pip install psycopg2-binary")
        if not url:
            raise ValueError("USERSTORE_POSTGRES_URL must be set for Postgres backend")
        self.conn = psycopg2.connect(url)
        self.conn.autocommit = True
        self._init_schema()

    def _init_schema(self):
        with self.conn.cursor() as cur:
            cur.execute("""
                CREATE TABLE IF NOT EXISTS transactions (
                    id BIGSERIAL PRIMARY KEY,
                    user_id TEXT NOT NULL,
                    txn_date DATE NOT NULL,
                    description TEXT,
                    amount NUMERIC(14,2),
                    category TEXT,
                    confidence TEXT,
                    created_at TIMESTAMPTZ DEFAULT NOW()
                );
                CREATE INDEX IF NOT EXISTS txn_user_date_idx ON transactions(user_id, txn_date);
                CREATE INDEX IF NOT EXISTS txn_user_cat_idx ON transactions(user_id, category);
            """)

    def add_transaction(self, user_id: str, txn: dict) -> None:
        with self.conn.cursor() as cur:
            cur.execute(
                "INSERT INTO transactions (user_id, txn_date, description, amount, category, confidence) "
                "VALUES (%s, %s, %s, %s, %s, %s)",
                (user_id, txn["date"], txn["description"], txn["amount"], txn["category"], txn.get("confidence", "")),
            )

    def list_transactions(self, user_id: str, month: str | None = None) -> list:
        sql = "SELECT txn_date, description, amount, category, confidence FROM transactions WHERE user_id = %s"
        params: list = [user_id]
        if month:
            sql += " AND to_char(txn_date, 'YYYY-MM') = %s"
            params.append(month)
        sql += " ORDER BY txn_date DESC"
        with self.conn.cursor() as cur:
            cur.execute(sql, params)
            return [
                {"date": str(r[0]), "description": r[1], "amount": float(r[2]), "category": r[3], "confidence": r[4]}
                for r in cur.fetchall()
            ]

    def summary(self, user_id: str, month: str | None = None) -> dict:
        sql = "SELECT category, SUM(amount), COUNT(*) FROM transactions WHERE user_id = %s"
        params: list = [user_id]
        if month:
            sql += " AND to_char(txn_date, 'YYYY-MM') = %s"
            params.append(month)
        sql += " GROUP BY category"
        with self.conn.cursor() as cur:
            cur.execute(sql, params)
            return {r[0]: {"total": float(r[1]), "count": int(r[2])} for r in cur.fetchall()}


class SQLiteUserStore:
    def __init__(self, db_path: str):
        import sqlite3
        Path(db_path).parent.mkdir(parents=True, exist_ok=True)
        self.conn = sqlite3.connect(db_path, check_same_thread=False)
        self._init_schema()

    def _init_schema(self):
        self.conn.executescript("""
            CREATE TABLE IF NOT EXISTS transactions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id TEXT NOT NULL,
                txn_date TEXT NOT NULL,
                description TEXT,
                amount REAL,
                category TEXT,
                confidence TEXT,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP
            );
            CREATE INDEX IF NOT EXISTS txn_user_date_idx ON transactions(user_id, txn_date);
            CREATE INDEX IF NOT EXISTS txn_user_cat_idx ON transactions(user_id, category);
        """)
        self.conn.commit()

    def add_transaction(self, user_id: str, txn: dict) -> None:
        self.conn.execute(
            "INSERT INTO transactions (user_id, txn_date, description, amount, category, confidence) "
            "VALUES (?, ?, ?, ?, ?, ?)",
            (user_id, txn["date"], txn["description"], float(txn["amount"]), txn["category"], txn.get("confidence", "")),
        )
        self.conn.commit()

    def list_transactions(self, user_id: str, month: str | None = None) -> list:
        sql = "SELECT txn_date, description, amount, category, confidence FROM transactions WHERE user_id = ?"
        params: list = [user_id]
        if month:
            sql += " AND substr(txn_date, 1, 7) = ?"
            params.append(month)
        sql += " ORDER BY txn_date DESC"
        cur = self.conn.execute(sql, params)
        return [
            {"date": r[0], "description": r[1], "amount": r[2], "category": r[3], "confidence": r[4]}
            for r in cur.fetchall()
        ]

    def summary(self, user_id: str, month: str | None = None) -> dict:
        return _aggregate(self.list_transactions(user_id, month))


def _aggregate(rows: list) -> dict:
    agg: dict = defaultdict(lambda: {"total": 0.0, "count": 0})
    for r in rows:
        cat = r.get("category", "Other")
        agg[cat]["total"] += float(r.get("amount", 0))
        agg[cat]["count"] += 1
    return {k: v for k, v in agg.items()}


class DocumentDBUserStore:
    """MongoDB-compatible transactions store. AWS DocumentDB / MongoDB Atlas."""

    def __init__(self, url: str, db_name: str = "budgetbot", tls_ca_file: str = ""):
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
        self.col = self.client[db_name]["transactions"]
        self.col.create_index([("user_id", 1), ("txn_date", -1)])
        self.col.create_index([("user_id", 1), ("category", 1)])

    def add_transaction(self, user_id: str, txn: dict) -> None:
        self.col.insert_one({
            "user_id": user_id,
            "txn_date": txn["date"],
            "description": txn["description"],
            "amount": float(txn["amount"]),
            "category": txn["category"],
            "confidence": txn.get("confidence", ""),
            "created_at": _now(),
        })

    def list_transactions(self, user_id: str, month: str | None = None) -> list:
        q: dict = {"user_id": user_id}
        if month:
            q["txn_date"] = {"$regex": f"^{month}"}
        return [
            {"date": d["txn_date"], "description": d["description"], "amount": d["amount"],
             "category": d["category"], "confidence": d.get("confidence", "")}
            for d in self.col.find(q).sort("txn_date", -1)
        ]

    def summary(self, user_id: str, month: str | None = None) -> dict:
        return _aggregate(self.list_transactions(user_id, month))


class MySQLUserStore:
    """RDS MySQL / Aurora MySQL adapter. Schema mirrors PostgresUserStore."""

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
                CREATE TABLE IF NOT EXISTS transactions (
                    id BIGINT AUTO_INCREMENT PRIMARY KEY,
                    user_id VARCHAR(255) NOT NULL,
                    txn_date DATE NOT NULL,
                    description TEXT,
                    amount DECIMAL(14,2),
                    category VARCHAR(64),
                    confidence VARCHAR(16),
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    INDEX idx_user_date (user_id, txn_date),
                    INDEX idx_user_cat (user_id, category)
                ) CHARACTER SET utf8mb4
            """)

    def add_transaction(self, user_id: str, txn: dict) -> None:
        with self.conn.cursor() as cur:
            cur.execute(
                "INSERT INTO transactions (user_id, txn_date, description, amount, category, confidence) "
                "VALUES (%s, %s, %s, %s, %s, %s)",
                (user_id, txn["date"], txn["description"], float(txn["amount"]),
                 txn["category"], txn.get("confidence", "")),
            )

    def list_transactions(self, user_id, month=None):
        sql = "SELECT txn_date, description, amount, category, confidence FROM transactions WHERE user_id = %s"
        params: list = [user_id]
        if month:
            sql += " AND DATE_FORMAT(txn_date, '%%Y-%%m') = %s"
            params.append(month)
        sql += " ORDER BY txn_date DESC"
        with self.conn.cursor() as cur:
            cur.execute(sql, params)
            return [
                {"date": str(r[0]), "description": r[1], "amount": float(r[2]),
                 "category": r[3], "confidence": r[4]}
                for r in cur.fetchall()
            ]

    def summary(self, user_id, month=None):
        sql = "SELECT category, SUM(amount), COUNT(*) FROM transactions WHERE user_id = %s"
        params: list = [user_id]
        if month:
            sql += " AND DATE_FORMAT(txn_date, '%%Y-%%m') = %s"
            params.append(month)
        sql += " GROUP BY category"
        with self.conn.cursor() as cur:
            cur.execute(sql, params)
            return {r[0]: {"total": float(r[1]), "count": int(r[2])} for r in cur.fetchall()}
