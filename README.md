# AI Knowledge Platform – RAG (On-Prem AI Assistant)

This repository contains a fully self-hosted, containerized **Retrieval-Augmented Generation (RAG)** platform designed for internal knowledge retrieval and secure private LLM interaction.

All components run **100% on-prem**, with **no external API calls**.

---

## What This Platform Does

This platform provides a secure internal AI assistant that:

* Searches internal SOPs, KBs, policies, and documents
* Answers questions with citations
* Operates entirely offline in isolated on-prem environments
* Uses a private RAG pipeline (ChromaDB + FastAPI + Indexer)
* Provides a user-friendly chat interface via Open WebUI

It’s built for research institutes, IT departments, and enterprises that cannot send documents to external cloud AI providers.

---

## Architecture Diagram

<p align="center">
  <img src="ai-platform-poc/docs/screenshots/architecture.png" width="700"/>
</p>

---

## Tech Stack

### Core Components
<div align="center">

| Component                    | Purpose                                                      |
|:---------------------------:|:------------------------------------------------------------:|
| **Open WebUI**              | Secure internal chat UI for interacting with LLMs + RAG       |
| **RAG API (FastAPI)**       | Handles semantic search, prompt building, and LLM calls        |
| **ChromaDB**                | Vector database storing embeddings and metadata               |
| **Indexer Service (Python)**| Processes documents, builds embeddings, tracks changes        |
| **Ollama**                  | Local LLM runtime (`phi-4`, `llama3`, `mistral`)              |
| **Caddy**                   | TLS termination + reverse proxy routing                       |
| **Docker Compose**          | Orchestration of all services                                 |

</div>

---

## How the System Works (High-Level Flow)

1. Internal KB folders (SMB or local) are mounted into the indexer container
2. Indexer scans, hashes, extracts, embeds, and updates ChromaDB
3. RAG API receives queries from Open WebUI
4. RAG API retrieves relevant chunks from ChromaDB
5. RAG API constructs a grounded prompt containing citations
6. RAG API sends the enriched prompt to Ollama
7. Open WebUI displays the generated answer + references

---

## Repository Structure

```
ai-platform-poc/
├── README.md
│
├── docs/
│   ├── architecture-overview.md
│   ├── rag-sequence-diagram.md
│   └── screenshots/
│       ├── architecture.png
│       └── rag-connection-tool.png
│
├── services/
│   ├── rag-api/
│   │   ├── rag-api.py
│   │   ├── Dockerfile
│   │   └── requirements.txt
│   │
│   ├── indexer/
│   │   ├── indexer.py
│   │   ├── Dockerfile
│   │   └── requirements.txt
│
├── deploy/
│   ├── caddy/
│   │   └── Caddyfile
│   ├── chromadb/
│   │   └── chromadb.yml
│   ├── openwebui/
│   │   └── openwebui.yml
│   └── compose-example.yml
│
├── kb-samples/
│
└── scripts/
```

---

## Environment Variables (`.env`) — Sanitized Example

```env
# RAG API
ADMIN_API_KEY=your-admin-key-here
CHROMA_HOST=chromadb
CHROMA_PORT=8000
COLLECTION_NAME=tli_kb

# Indexer
KB_ROOT=/kb
INDEXER_SCHEDULE_SECONDS=900

# Ollama
OLLAMA_HOST=http://ollama:11434
OLLAMA_MODEL=phi4
```

Always sanitize and never commit real secrets.

---

## RAG API Endpoints

### **POST /query**

Query the knowledge base using semantic search + RAG.

**Example:**

```bash
curl -X POST http://localhost:9000/query \
  -H "Content-Type: application/json" \
  -d '{
    "query": "How do I reset a laptop password?",
    "top_k": 3
  }'
```

**Response Includes:**

* LLM-generated answer
* Retrieved chunks
* Citations

---

### **GET /health**

Basic health check.

---

### **GET /admin/status**

Admin-only status endpoint (requires `X-Admin-Key` header).

**Returns:**

* Indexer last run
* Last error (if any)
* File counts
* Docs indexed
* Deleted docs detected
* Active KB roots

---

## Indexer Service (v2)

The indexer performs:

### **1. Recursive Directory Scanning**

Finds all documents across mounted KB paths.

### **2. File Hashing**

Prevents redundant re-indexing when files haven’t changed.

### **3. Multi-format Ingestion**

Supports:

* PDF
* DOCX
* Markdown
* TXT
* CSV / Excel

### **4. Chunking & Embedding**

Splits documents into optimal vector-friendly chunks.

### **5. Deletion Tracking**

If a file is removed → the corresponding ChromaDB record is deleted.

### **6. Status Reporting**

Sends heartbeat data to `/admin/status` for observability.

---

## Roadmap

* Scheduled automatic reindexing
* Role-based filtering for search results
* Multi-collection / namespace-aware queries
* Audit logging and history tracking
* Namespace-level access control
* Automatic model fallback + smart routing

---

**See more details:**
📄 [docs/architecture-overview.md](https://github.com/Dv-beep/ai-platform-poc/blob/main/ai-poc/docs/architecture-overview.md)
