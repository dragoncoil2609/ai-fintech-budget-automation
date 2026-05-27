"""Object storage adapters (raw uploaded CSVs/PDFs). Same interface as StudyBot."""
from pathlib import Path


class S3Storage:
    def __init__(self, bucket: str, region: str):
        import boto3
        if not bucket:
            raise ValueError("STORAGE_BUCKET must be set for S3 backend")
        self.s3 = boto3.client("s3", region_name=region)
        self.bucket = bucket

    def put(self, key: str, data: bytes) -> str:
        self.s3.put_object(Bucket=self.bucket, Key=key, Body=data)
        return f"s3://{self.bucket}/{key}"

    def get(self, key: str) -> bytes:
        return self.s3.get_object(Bucket=self.bucket, Key=key)["Body"].read()

    def list(self, prefix: str = "") -> list:
        resp = self.s3.list_objects_v2(Bucket=self.bucket, Prefix=prefix)
        return [obj["Key"] for obj in resp.get("Contents", [])]


class LocalStorage:
    def __init__(self, base_dir: str):
        self.base = Path(base_dir)
        self.base.mkdir(parents=True, exist_ok=True)

    def put(self, key: str, data: bytes) -> str:
        path = self.base / key
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(data)
        return f"file://{path.resolve()}"

    def get(self, key: str) -> bytes:
        return (self.base / key).read_bytes()

    def list(self, prefix: str = "") -> list:
        return [
            str(p.relative_to(self.base))
            for p in self.base.rglob("*") if p.is_file() and str(p.relative_to(self.base)).startswith(prefix)
        ]
