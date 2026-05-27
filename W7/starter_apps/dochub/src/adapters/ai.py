"""AI adapters for DocHub.

DocHub uses RAG with tenant-aware retrieval. The interface mirrors StudyBot but
the retrieve_and_generate call always passes a tenant_id filter.
"""
from typing import Any


class BedrockAI:
    def __init__(self, region: str, model_id: str):
        import boto3
        self.region = region
        self.model_id = model_id
        self.runtime = boto3.client("bedrock-runtime", region_name=region)
        self.agent_runtime = boto3.client("bedrock-agent-runtime", region_name=region)

    def invoke(self, prompt: str, **kwargs: Any) -> str:
        resp = self.runtime.converse(
            modelId=self.model_id,
            messages=[{"role": "user", "content": [{"text": prompt}]}],
            inferenceConfig={
                "maxTokens": kwargs.get("max_tokens", 1024),
                "temperature": kwargs.get("temperature", 0.2),
            },
        )
        return resp["output"]["message"]["content"][0]["text"]

    def retrieve_and_generate(self, query: str, kb_id: str, tenant_id: str) -> dict:
        """RAG with tenant isolation enforced at retrieval time."""
        if not kb_id:
            raise ValueError("VECTOR_BEDROCK_KB_ID must be set")
        model_arn = f"arn:aws:bedrock:{self.region}::foundation-model/{self.model_id}"
        resp = self.agent_runtime.retrieve_and_generate(
            input={"text": query},
            retrieveAndGenerateConfiguration={
                "type": "KNOWLEDGE_BASE",
                "knowledgeBaseConfiguration": {
                    "knowledgeBaseId": kb_id,
                    "modelArn": model_arn,
                    "retrievalConfiguration": {
                        "vectorSearchConfiguration": {
                            "filter": {"equals": {"key": "tenant_id", "value": tenant_id}}
                        }
                    },
                },
            },
        )
        return {
            "answer": resp["output"]["text"],
            "citations": [
                {
                    "text": ref.get("content", {}).get("text", ""),
                    "source": ref.get("location", {}),
                }
                for citation in resp.get("citations", [])
                for ref in citation.get("retrievedReferences", [])
            ],
        }


class LocalAI:
    def invoke(self, prompt: str, **kwargs: Any) -> str:
        snippet = prompt[:200].replace("\n", " ")
        return f"[LOCAL_AI_STUB] Received prompt: {snippet!r}..."

    def retrieve_and_generate(self, query: str, kb_id: str, tenant_id: str) -> dict:
        return {
            "answer": (
                f"[LOCAL_AI_STUB] Tenant={tenant_id} asked: {query!r}. "
                "Switch AI_BACKEND=bedrock + VECTOR_BACKEND=bedrock_kb for real RAG."
            ),
            "citations": [],
        }
