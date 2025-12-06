"""
RAG API

FastAPI service that fronts a ChromaDB collection. Provides:

- POST /ingest:
    Indexer pushes pre-chunked documents with doc_hash + last_modified

- POST /query:
    Clients request top-k relevant chunks for a natural language query

- GET /health:
    Basic health check

- GET /admin/status:
    Admin-only status + document count + last indexer heartbeat

- POST /admin/indexer_status:
    Indexer sends status/heartbeat payload

- POST /delete_document:
    Admin-only delete by document_id (used by indexer)
"""

import os
from typing import List, Dict, Any, Optional

import chromadb
from chromadb.config import Settings
from fastapi import FastAPI, Header, HTTPException
from pydantic import BaseModel, Field

# --- Environment / config ---

CHROMA_HOST = os.environ.get("CHROMA_HOST", "chromadb")
CHROMA_PORT = int(os.environ.get("CHROMA_PORT", "8000"))
COLLECTION_NAME = os.environ.get("COLLECTION_NAME", "tli_kb")
ADMIN_API_KEY = os.environ.get("ADMIN_API_KEY")  # optional admin key

app = FastAPI(title="RAG API")

# --- Chroma client and collection ---

client = chromadb.HttpClient(
    host=CHROMA_HOST,
    port=CHROMA_PORT,
    settings=Settings(allow_reset=False),
)
collection = client.get_or_create_collection(COLLECTION_NAME)

# In-memory store for latest indexer status heartbeat
LAST_INDEXER_STATUS: Optional[Dict[str, Any]] = None


# ---------- Pydantic models ----------

class Chunk(BaseModel):
    id: str
    text: str
    metadata: Dict[str, Any] = Field(default_factory=dict)


class IngestRequest(BaseModel):
    document_id: str
    chunks: List[Chunk]

    # Optional extras from the indexer
    doc_hash: Optional[str] = None          # sha256 or similar
    last_modified: Optional[str] = None     # ISO8601 string (e.g. 2025-12-01T21:30:00Z)


class QueryRequest(BaseModel):
    query: str
    top_k: int = 5


class QueryResult(BaseModel):
    id: str
    text: str
    metadata: Dict[str, Any]
    version: Optional[int] = None
    last_modified: Optional[str] = None


class QueryResponse(BaseModel):
    results: List[QueryResult]


class DeleteDocumentRequest(BaseModel):
    document_id: str


class IndexerStatusPayload(BaseModel):
    last_run: Optional[str] = None
    last_error: Optional[str] = None
    kb_roots: List[str] = Field(default_factory=list)
    files_seen: int = 0
    docs_indexed: int = 0
    deleted_docs: int = 0


# ---------- Helpers ----------

def require_admin(x_admin_key: Optional[str]) -> None:
    """
    Simple admin-key check for admin endpoints.
    If ADMIN_API_KEY is set, the header must match.
    If ADMIN_API_KEY is not set, allow all (useful for local dev).
    """
    if ADMIN_API_KEY and x_admin_key != ADMIN_API_KEY:
        raise HTTPException(status_code=401, detail="Invalid admin key")


# ---------- Endpoints ----------

@app.post("/ingest")
def ingest(req: IngestRequest):
    """
    Ingest pre-chunked text into Chroma.
    Called by the indexer service, not end users.
    """

    if not req.chunks:
        return {"status": "no_chunks"}

    # ---- Check existing document to support hash + versioning ----
    existing = collection.get(
        where={"document_id": req.document_id},
        include=["metadatas"],
    )

    existing_metadatas = existing.get("metadatas") or []
    existing_doc_hash: Optional[str] = None
    existing_version: int = 0

    # Chroma returns metadatas as a list of lists: [ [meta1, meta2, ...] ]
    if existing_metadatas and existing_metadatas[0]:
        first_meta = existing_metadatas[0][0]
        existing_doc_hash = first_meta.get("doc_hash")
        existing_version = int(first_meta.get("version", 0))

    # If hash matches, skip re-indexing this document
    if req.doc_hash and existing_doc_hash and req.doc_hash == existing_doc_hash:
        return {
            "status": "skipped_unchanged",
            "ingested": 0,
            "document_id": req.document_id,
            "doc_hash": req.doc_hash,
        }

    # Bump version if we already had this doc
    new_version = existing_version + 1

    # ---- Build docs / ids / metadatas for upsert ----
    docs = [c.text for c in req.chunks]
    ids = [c.id for c in req.chunks]

    metadatas: List[Dict[str, Any]] = []
    for c in req.chunks:
        meta = dict(c.metadata or {})
        meta.setdefault("document_id", req.document_id)
        meta["version"] = new_version

        if req.doc_hash:
            meta["doc_hash"] = req.doc_hash
        if req.last_modified:
            meta["last_modified"] = req.last_modified

        metadatas.append(meta)

    # ---- Delete old chunks for this document to avoid stale data ----
    collection.delete(where={"document_id": req.document_id})

    # ---- Upsert new chunks ----
    collection.upsert(
        documents=docs,
        ids=ids,
        metadatas=metadatas,
    )

    return {
        "status": "ok",
        "ingested": len(ids),
        "document_id": req.document_id,
        "version": new_version,
        "doc_hash": req.doc_hash,
        "last_modified": req.last_modified,
    }


@app.post("/query", response_model=QueryResponse)
def query(req: QueryRequest):
    """
    Query the vector store for the most relevant chunks.

    Typically called by a tool server / WebUI as part of a RAG pipeline.
    """
    res = collection.query(
        query_texts=[req.query],
        n_results=req.top_k,
        include=["documents", "metadatas"],
    )

    out: List[QueryResult] = []

    ids_lists = res.get("ids") or []
    docs_lists = res.get("documents") or []
    metas_lists = res.get("metadatas") or []

    if ids_lists and ids_lists[0]:
        for i, _id in enumerate(ids_lists[0]):
            doc_text = docs_lists[0][i] if docs_lists and docs_lists[0] else ""
            meta = metas_lists[0][i] if metas_lists and metas_lists[0] else {}

            out.append(
                QueryResult(
                    id=_id,
                    text=doc_text,
                    metadata=meta,
                    version=meta.get("version"),
                    last_modified=meta.get("last_modified"),
                )
            )

    return QueryResponse(results=out)


@app.post("/delete_document")
def delete_document(
    req: DeleteDocumentRequest,
    x_admin_key: Optional[str] = Header(None, alias="X-Admin-Key"),
):
    """
    Delete all chunks for a given document_id.
    Used by the indexer when files are removed from disk.
    """
    require_admin(x_admin_key)

    # Chroma's delete returns None, so we just acknowledge the request
    collection.delete(where={"document_id": req.document_id})

    return {
        "status": "ok",
        "deleted_document_id": req.document_id,
    }


@app.post("/admin/indexer_status")
def admin_indexer_status(
    status: IndexerStatusPayload,
    x_admin_key: Optional[str] = Header(None, alias="X-Admin-Key"),
):
    """
    Receive indexer heartbeat/status.
    Called by the indexer at the end of a run.
    """
    require_admin(x_admin_key)

    global LAST_INDEXER_STATUS
    LAST_INDEXER_STATUS = status.dict()

    return {"status": "ok"}


@app.get("/admin/status")
def admin_status(
    x_admin_key: Optional[str] = Header(None, alias="X-Admin-Key"),
):
    """
    Admin-only status & metadata endpoint.

    Used by:
    - indexer (to decide on reset/full rebuild via document_count)
    - operators (health & last indexer status)
    """
    require_admin(x_admin_key)

    try:
        document_count = collection.count()
    except Exception:
        document_count = 0

    return {
        "status": "ok",
        "collection": COLLECTION_NAME,
        "document_count": document_count,
        "indexer_status": LAST_INDEXER_STATUS,
    }


@app.get("/health")
def health():
    """
    Basic health check endpoint.
    """
    return {"status": "ok", "collection": COLLECTION_NAME}
