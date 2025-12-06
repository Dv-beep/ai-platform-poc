# Indexer Service (v2)

The Indexer Service is responsible for scanning knowledge base directories, extracting text, chunking content, generating metadata, and synchronizing the data with the vector database through the RAG API. It ensures that ChromaDB always reflects the current state of your internal knowledge base (KB).

The indexer runs as a standalone Docker service and is fully automated.

---

## Key Responsibilities

### **1. Directory Scanning**

The indexer recursively walks all configured KB roots:

```
/kb/knowledgebase
/kb/sops
/kb/datasets
```

Hidden directories (`.git`, `.cache`, etc.) are automatically ignored.

---

### **2. Multi-Format File Support**

The indexer extracts text from the following file types:

| Format                         | Supported | Extraction Method     |
| ------------------------------ | --------- | --------------------- |
| **TXT / MD / LOG**             | ✅         | UTF-8 text reader     |
| **PDF**                        | ✅         | `pypdf`               |
| **DOCX**                       | ✅         | `python-docx`         |
| **CSV**                        | ✅         | Pandas (`read_csv`)   |
| **Excel (.xlsx, .xls, .xlsm)** | ✅         | Pandas (`read_excel`) |

Each sheet within an Excel workbook is labeled so the LLM understands context.

---

### **3. File Hashing & Change Detection**

Before ingesting a file, the indexer:

1. Computes a **SHA-256 hash**
2. Compares it against `index_state.json`
3. If unchanged → the file is skipped
4. If changed → the file is re-ingested

This prevents unnecessary re-embeddings and speeds up indexing.

---

### **4. Chunking**

Documents are split into ~**1500-character** chunks, cut cleanly on whitespace or newlines when possible.

Each chunk includes metadata:

```json
{
  "path": "policy.docx",
  "source": "sops",
  "file_type": "docx",
  "chunk_index": 0,
  "chunk_count": 8,
  "document_id": "sops/policy.docx",
  "source_path": "/kb/sops/policy.docx"
}
```

---

### **5. Ingest API Integration**

For each changed file, the indexer calls:

```
POST /ingest
```

Body shape:

```json
{
  "document_id": "sops/policy.docx",
  "doc_hash": "<sha256>",
  "last_modified": "2025-01-01T10:00:00Z",
  "chunks": [ ... ]
}
```

If ingestion succeeds, the new hash is stored in `index_state.json`.

---

### **6. Deletion Detection**

If a file is removed from disk, the indexer calls:

```
POST /delete_document
```

This removes all associated chunks from ChromaDB.

A safety system prevents accidental mass deletion if a mount point goes missing:

* If SMB mount is **not healthy** → indexing is aborted
* If a KB root is removed from config → deletion is skipped unless
  `ALLOW_ROOT_REMOVAL=true`

---

### **7. Health & Status Reporting**

After every run, the indexer pushes a heartbeat to:

```
POST /admin/indexer_status
```

Payload includes:

* `last_run`
* `last_error`
* `kb_roots`
* `files_seen`
* `docs_indexed`
* `deleted_docs`

This allows observability from the RAG API or your logs/UI.

---

### **8. Mount Safety Checks**

To prevent data loss, indexing stops entirely if a KB directory is not properly mounted.

A mount must:

* Be a directory
* Be an active mount point (`os.path.ismount`)
* Contain files

If not → the deletion pass is disabled to avoid wiping Chroma.

---

## Environment Variables (Sanitized)

```env
KB_ROOTS=/kb/knowledgebase,/kb/sops,/kb/datasets
RAG_API_URL=http://rag-api:9000
ADMIN_API_KEY=your-admin-key-here

# Prevents accidental deletion when a root disappears
ALLOW_ROOT_REMOVAL=false

# Optional override for status reporting endpoint
INDEXER_STATUS_ENDPOINT=http://rag-api:9000/admin/indexer_status
```

---

## Summary

The Indexer Service provides:

* Automated ingestion
* Change-based reindexing
* Deletion synchronization
* Multi-format document extraction
* ChromaDB consistency
* Safe SMB mount handling
* Status reporting for observability

It’s the backbone that keeps your private AI knowledge system up-to-date without manual intervention.
