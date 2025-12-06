# RAG API Service

This service provides the HTTP API layer for the AI Knowledge Platform’s Retrieval-Augmented Generation (RAG) pipeline. It fronts a ChromaDB collection and exposes endpoints for:

- Ingesting pre-chunked documents from the Indexer
- Querying the vector store for relevant chunks
- Managing document deletions
- Reporting and inspecting Indexer status
- Basic health checks

All calls are internal to the platform and can be protected via an admin key.

---

## Tech Stack

- **Framework:** FastAPI  
- **Vector DB:** ChromaDB (HTTP client)  
- **Language:** Python 3  
- **Containerized:** Yes (Docker)  

---

## Environment Variables (Sanitized)

These are typically set via `docker-compose` or a `.env` file.

```env
# Chroma connection
CHROMA_HOST=chromadb
CHROMA_PORT=8000
COLLECTION_NAME=tli_kb

# Optional admin key for protected endpoints
ADMIN_API_KEY=${X-Admin-Key}

---

Absolutely — here is a **clean, standalone “Endpoints” section** you can paste directly into a README.md.
It is fully aligned with your updated `main.py`, sanitized, and formatted for GitHub.

---

# 📡 RAG API Endpoints

Below are all public and admin endpoints exposed by the RAG API.
These match the updated `main.py` exactly.

---

## **POST /query**

Query the vector database for top-K relevant chunks.

**Request:**

```json
{
  "query": "How do I reset a laptop password?",
  "top_k": 5
}
```

**Response:**

```json
{
  "results": [
    {
      "id": "sops/laptop_reset.docx#chunk-0",
      "text": "SOP Title: Laptop Password Reset Procedure ...",
      "metadata": {
        "document_id": "sops/laptop_reset.docx",
        "source": "sops",
        "file_type": "docx",
        "chunk_index": 0,
        "chunk_count": 4,
        "version": 2,
        "last_modified": "2025-01-15T10:00:00Z"
      },
      "version": 2,
      "last_modified": "2025-01-15T10:00:00Z"
    }
  ]
}
```

---

## **POST /ingest**

Indexer-only endpoint for ingesting pre-chunked documents.

**Used by:** Indexer Service
**Not used by:** End users, WebUI

**Request body:**

```json
{
  "document_id": "sops/policy.docx",
  "doc_hash": "sha256-hash-here",
  "last_modified": "2025-01-01T10:00:00Z",
  "chunks": [
    {
      "id": "sops/policy.docx#chunk-0",
      "text": "First chunk...",
      "metadata": {
        "path": "policy.docx",
        "source": "sops",
        "file_type": "docx",
        "chunk_index": 0,
        "chunk_count": 8,
        "document_id": "sops/policy.docx",
        "source_path": "/kb/sops/policy.docx"
      }
    }
  ]
}
```

**Behavior:**

* Skips if `doc_hash` matches current version
* Otherwise deletes all old chunks for this document
* Upserts new chunks with incremented `version`

**Response:**

```json
{
  "status": "ok",
  "ingested": 8,
  "document_id": "sops/policy.docx",
  "version": 3,
  "doc_hash": "sha256-hash-here",
  "last_modified": "2025-01-01T10:00:00Z"
}
```

---

## **POST /delete_document** (Admin)

Delete all chunks for a specific `document_id`.

> Used exclusively by the Indexer when a file is deleted from disk.

**Headers (if admin key is set):**

```http
X-Admin-Key: your-admin-key
```

**Body:**

```json
{
  "document_id": "sops/policy.docx"
}
```

**Response:**

```json
{
  "status": "ok",
  "deleted_document_id": "sops/policy.docx"
}
```

---

## **POST /admin/indexer_status** (Admin)

Indexer heartbeat endpoint — the Indexer calls this at the end of each run.

**Sent by Indexer:**

```json
{
  "last_run": "2025-01-01T12:00:00Z",
  "last_error": null,
  "kb_roots": ["/kb/knowledgebase", "/kb/sops", "/kb/datasets"],
  "files_seen": 120,
  "docs_indexed": 5,
  "deleted_docs": 1
}
```

**Headers:**

```http
X-Admin-Key: your-admin-key
```

**Response:**

```json
{
  "status": "ok"
}
```

---

## **GET /admin/status** (Admin)

Returns:

* ChromaDB document count
* Last indexer heartbeat
* Collection name
* Status metadata

**Headers:**

```http
X-Admin-Key: your-admin-key
```

**Response:**

```json
{
  "status": "ok",
  "collection": "tli_kb",
  "document_count": 342,
  "indexer_status": {
    "last_run": "2025-01-01T12:00:00Z",
    "last_error": null,
    "kb_roots": ["/kb/knowledgebase", "/kb/sops", "/kb/datasets"],
    "files_seen": 120,
    "docs_indexed": 5,
    "deleted_docs": 1
  }
}
```

---

## **GET /health**

Basic service health check.

**Response:**

```json
{
  "status": "ok",
  "collection": "tli_kb"
}
```
