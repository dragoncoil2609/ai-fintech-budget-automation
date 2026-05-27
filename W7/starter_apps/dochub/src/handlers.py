"""DocHub business logic with multi-tenant enforcement.

CRITICAL: tenant_id is a required argument to every handler. The vector store
filters on it; the userstore partitions on it; the S3 key prefixes use it. A bug
in any single layer is mitigated by isolation in the others (defense in depth).
"""
import io
import uuid
from typing import Optional


PROMPT_TEMPLATE = """You are a document intelligence assistant for a multi-tenant SaaS
platform. Answer the user's question using ONLY the documents from their organization
({tenant_id}). NEVER reference documents from other organizations. Cite the source
document by name when answering. If the answer is not in the provided context, say
"I could not find this information in your organization's documents."

CONTEXT:
{context}

QUESTION: {question}

ANSWER:"""


def _extract_text(filename: str, data: bytes) -> str:
    name = filename.lower()
    if name.endswith(".pdf"):
        try:
            from pypdf import PdfReader
        except ImportError:
            return "(pypdf not installed)"
        reader = PdfReader(io.BytesIO(data))
        return "\n\n".join(page.extract_text() or "" for page in reader.pages)
    try:
        return data.decode("utf-8", errors="replace")
    except Exception:
        return ""


def handle_upload(
    tenant_id: str,
    user_id: str,
    filename: str,
    doc_type: str,
    data: bytes,
    storage,
    userstore,
    vector_store,
) -> dict:
    doc_id = str(uuid.uuid4())
    # Tenant-isolated S3 key prefix
    key = f"{tenant_id}/{doc_id}/{filename}"
    location = storage.put(key, data)
    text = _extract_text(filename, data)
    if text.strip():
        vector_store.ingest(
            doc_id=doc_id, text=text, tenant_id=tenant_id,
            metadata={"filename": filename, "doc_type": doc_type, "uploaded_by": user_id},
        )
    userstore.add_doc(
        tenant_id=tenant_id, doc_id=doc_id,
        metadata={
            "filename": filename, "doc_type": doc_type, "uploaded_by": user_id,
            "size": len(data), "location": location, "chars": len(text),
        },
    )
    return {
        "tenant_id": tenant_id, "doc_id": doc_id,
        "filename": filename, "doc_type": doc_type,
        "size": len(data), "chars_extracted": len(text), "location": location,
    }


def handle_query(
    tenant_id: str,
    question: str,
    ai_client,
    vector_store,
    vector_backend: str,
    bedrock_kb_id: str,
) -> dict:
    if vector_backend == "bedrock_kb":
        result = ai_client.retrieve_and_generate(query=question, kb_id=bedrock_kb_id, tenant_id=tenant_id)
        return {"question": question, **result}
    # Local path
    chunks = vector_store.search(question, tenant_id=tenant_id, top_k=5)
    if not chunks:
        return {
            "question": question,
            "answer": "I could not find this information in your organization's documents.",
            "citations": [],
        }
    context = "\n\n".join(
        f"[{i+1}] (doc={c['metadata'].get('filename', c['doc_id'])}) {c['text']}"
        for i, c in enumerate(chunks)
    )
    prompt = PROMPT_TEMPLATE.format(tenant_id=tenant_id, context=context, question=question)
    answer = ai_client.invoke(prompt, max_tokens=512)
    citations = [
        {
            "rank": i + 1, "doc_id": c["doc_id"], "score": c["score"],
            "filename": c["metadata"].get("filename"),
            "doc_type": c["metadata"].get("doc_type"),
            "text": c["text"][:200],
        }
        for i, c in enumerate(chunks)
    ]
    return {"question": question, "answer": answer, "citations": citations}


def handle_list_docs(tenant_id: str, doc_type: Optional[str], userstore) -> dict:
    return {
        "tenant_id": tenant_id,
        "doc_type_filter": doc_type,
        "docs": userstore.list_docs(tenant_id, doc_type=doc_type),
    }
