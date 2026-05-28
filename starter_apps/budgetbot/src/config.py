"""Env-driven config for BudgetBot."""
import os
from dataclasses import dataclass

try:
    # pyrefly: ignore [missing-import]
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass


def _env(name: str, default: str = "") -> str:
    return os.getenv(name, default)


@dataclass(frozen=True)
class Config:
    ai_backend: str = _env("AI_BACKEND", "local")
    ai_model_id: str = _env("AI_MODEL_ID", "meta.llama3-1-70b-instruct-v1:0")
    aws_region: str = _env("AWS_REGION") or _env("AWS_REGION_NAME") or "us-west-2"

    storage_backend: str = _env("STORAGE_BACKEND", "local")
    storage_bucket: str = _env("STORAGE_BUCKET", "")
    s3_bucket: str = _env("S3_BUCKET", "")
    s3_presign_expiry: int = int(_env("S3_PRESIGN_EXPIRY", "900"))
    max_upload_size: int = int(_env("MAX_UPLOAD_SIZE_MB", "50")) * 1024 * 1024  # bytes, default 50 MB
    sqs_queue_url: str = _env("SQS_QUEUE_URL", "")


    userstore_backend: str = _env("USERSTORE_BACKEND", "sqlite")
    userstore_table: str = _env("USERSTORE_TABLE", "")
    userstore_postgres_url: str = _env("USERSTORE_POSTGRES_URL", "")
    userstore_sqlite_path: str = _env("USERSTORE_SQLITE_PATH", "./_data/transactions.db")

    default_user_id: str = _env("DEFAULT_USER_ID", "test-user-001")
    log_level: str = _env("LOG_LEVEL", "INFO")


    # Frontend serving (opt-out so backend can be pure API for split deploys)
    serve_frontend: bool = _env("SERVE_FRONTEND", "true").lower() == "true"
    cors_origins: str = _env("CORS_ORIGINS", "*")

    # Extra DB backends (DocumentDB, MySQL)
    userstore_mongo_url: str = _env("USERSTORE_MONGO_URL", "")
    userstore_mongo_db: str = _env("USERSTORE_MONGO_DB", "budgetbot")
    userstore_mongo_tls_ca: str = _env("USERSTORE_MONGO_TLS_CA", "")
    userstore_mysql_url: str = _env("USERSTORE_MYSQL_URL", "")

    def __post_init__(self):
        # Nếu có cấu hình DB_SECRET_NAME, tự động gọi Secrets Manager lấy thông tin DB và sinh postgres url
        secret_name = _env("DB_SECRET_NAME", "")
        if secret_name and self.userstore_backend == "postgres":
            import boto3
            import json
            try:
                client = boto3.client("secretsmanager", region_name=self.aws_region)
                response = client.get_secret_value(SecretId=secret_name)
                secret = json.loads(response["SecretString"])
                
                # Giải nén thông tin từ secret (Hỗ trợ cả chữ hoa DB_ và chữ thường mặc định của AWS)
                username = secret.get("DB_USER") or secret.get("username") or "postgres"
                password = secret.get("DB_PASSWORD") or secret.get("password") or ""
                host = secret.get("DB_HOST") or secret.get("host") or ""
                port = secret.get("DB_PORT") or secret.get("port") or 5432
                dbname = secret.get("DB_NAME") or secret.get("dbname") or "budgetbot"
                
                # Cấu hình lại thuộc tính userstore_postgres_url động hỗ trợ SSL cho RDS Cloud
                sslmode = _env("DB_SSLMODE") or "require"
                url = f"postgresql://{username}:{password}@{host}:{port}/{dbname}?sslmode={sslmode}"
                object.__setattr__(self, "userstore_postgres_url", url)
                print(f"[SecretsManager] Successfully loaded credentials from {secret_name}")
            except Exception as e:
                print(f"[SecretsManager] Error loading credentials from secret {secret_name}: {e}")

config = Config()
