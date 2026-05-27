"""Vector store with tenant-aware filtering. Same shape as StudyBot but every
operation receives tenant_id and pushes it into metadata.
"""
import re
from collections import Counter
from typing import Optional


class BedrockKBVector:
    def __init__(self, kb_id: str, region: str):
        import boto3
        if not kb_id:
            raise ValueError("VECTOR_BEDROCK_KB_ID must be set")
        self.kb_id = kb_id
        self.agent_runtime = boto3.client("bedrock-agent-runtime", region_name=region)

    def ingest(self, doc_id: str, text: str, tenant_id: str, metadata: Optional[dict] = None) -> None:
        # KB ingestion is async via S3 trigger. This adapter is search-side only.
        # Make sure your upstream S3 → KB pipeline writes tenant_id into the
        # metadata.json sidecar file Bedrock KB expects.
        pass

    def search(self, query: str, tenant_id: str, top_k: int = 5) -> list:
        resp = self.agent_runtime.retrieve(
            knowledgeBaseId=self.kb_id,
            retrievalQuery={"text": query},
            retrievalConfiguration={
                "vectorSearchConfiguration": {
                    "numberOfResults": top_k,
                    "filter": {"equals": {"key": "tenant_id", "value": tenant_id}},
                }
            },
        )
        return [
            {
                "text": r.get("content", {}).get("text", ""),
                "doc_id": r.get("metadata", {}).get("doc_id", ""),
                "score": r.get("score", 0.0),
                "metadata": r.get("metadata", {}),
            }
            for r in resp.get("retrievalResults", [])
        ]


class LocalVector:
    """In-memory keyword index with tenant_id filter — for local development."""

    def __init__(self):
        self.docs: list[tuple[str, str, dict]] = []

    @staticmethod
    def _tokens(text: str) -> list:
        return [t.lower() for t in re.findall(r"\w+", text) if len(t) > 2]

    @staticmethod
    def _chunk(text: str, size: int = 500) -> list:
        sentences = re.split(r"(?<=[.!?])\s+", text)
        chunks, current = [], ""
        for s in sentences:
            if len(current) + len(s) < size:
                current += " " + s
            else:
                if current.strip():
                    chunks.append(current.strip())
                current = s
        if current.strip():
            chunks.append(current.strip())
        return chunks or [text]

    def ingest(self, doc_id: str, text: str, tenant_id: str, metadata: Optional[dict] = None) -> None:
        md = metadata or {}
        for i, chunk in enumerate(self._chunk(text)):
            self.docs.append((
                f"{doc_id}#{i}", chunk,
                {**md, "tenant_id": tenant_id, "doc_id": doc_id, "chunk_idx": i},
            ))

    def search(self, query: str, tenant_id: str, top_k: int = 5) -> list:
        q_tokens = set(self._tokens(query))
        results = []
        for chunk_id, text, md in self.docs:
            # CRITICAL: tenant isolation enforced at retrieval layer.
            # A bug in handler code cannot leak cross-tenant results.
            if md.get("tenant_id") != tenant_id:
                continue
            d_tokens = Counter(self._tokens(text))
            score = sum(d_tokens[t] for t in q_tokens)
            if score > 0:
                results.append({
                    "text": text,
                    "doc_id": md.get("doc_id", chunk_id),
                    "score": float(score),
                    "metadata": md,
                })
        results.sort(key=lambda r: -r["score"])
        return results[:top_k]
