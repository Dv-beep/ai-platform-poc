# AI Knowledge Platform – RAG (On-Prem AI Assistant)

This repository contains a fully self-hosted, containerized **Retrieval-Augmented Generation (RAG)** platform designed for internal organizational knowledge retrieval and secure private LLM interaction.

All components run 100% on-prem, with no external API calls.

---

## What This Platform Does

This project provides a secure internal AI assistant that:

  - Searches internal SOPs, KBs, policies, and documents
  - Answers questions with citations
  - Works offline, fully on-premises
  - Uses an internal RAG pipeline (ChromaDB + custom FastAPI + embedding/indexer service)
  - Exposes a secure chat interface for end users via Open WebUI

It’s designed to serve research institutes, IT departments, labs, and enterprises that can’t send internal documents to external cloud AI services.

---

## Architecture Diagram

<p align="center">
  <img src="ai-poc/docs/screenshots/architecture.png" width="700"/>
</p>

---

## Tech Stack

** Core Components
| Component                    | Purpose                                                      |
| ---------------------------- | ------------------------------------------------------------ |
| **Open WebUI**               | Secure internal chat UI for interacting with LLMs + RAG      |
| **RAG API (FastAPI)**        | Handles semantic search, prompt building, and LLM calls      |
| **ChromaDB**                 | Vector database storing embeddings + metadata                |
| **Indexer Service (Python)** | Reads/embeds documents, pushes to ChromaDB, tracks deletions |
| **Ollama**                   | Local LLM runtime (e.g., `phi-4`, `llama3`, `mistral`)       |
| **Caddy**                    | TLS termination + reverse proxy routing                      |
| **Docker Compose**           | Orchestration of all services                                |

---

## How the System Works (High-Level Flow)
1. Internal KB folders (SMB or local) are mounted into the indexer container
2. Indexer scans, hashes, extracts, embeds, and updates ChromaDB
3. RAG API receives queries from Open WebUI
4. RAG API retrieves relevant chunks from ChromaDB
5. RAG API constructs a grounded prompt including citations
6. RAG API calls Ollama locally
7. Open WebUI displays the answer + source references

---

## Repository Structure
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

---

## Environment Variables (.env) — Sanitized Example
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

---

## RAG API Endpoints
***POST /query
Query the knowledge base using semantic search + RAG

Example:
curl -X POST http://localhost:9000/query \
  -H "Content-Type: application/json" \
  -d '{
    "query": "How do I reset a laptop password?",
    "top_k": 3
  }'
Response includes:
- Answer (LLM-generated)
- Retrieved chunks
- Citations

---

***GET /health
Basic health check

---

***GET /admin/status
Admin-only status endpoint (protected by <code>X-Admin-Key</code> header).

Returns:
-Indexer last run
-Last error (if any)
- File counts
- Docs indexed
- Deleted docs removed
- Current KB roots

---

##Indexer Service (v2)
The indexer performs:

1. Recursive directory walking
Scans all mounted KB paths.

2. File hashing
Detects changes and avoids re-indexing duplicates.

3. Supports multiple formats
- PDF
- DOCX
- TXT
- CSV / Excel
- Markdown

4. Chunking & embedding
Breaks documents into optimal chunks.

5. Deletion tracking
If a file is removed from disk → removed from ChromaDB.

6. Status reporting
Sends heartbeat to <code>/admin/status</code> endpoint (optional).

---

##Roadmap
- Scheduled embedded re-indexing
- Role-based result filtering

```

See [docs/arhitecture-overview.md](https://github.com/Dv-beep/ai-platform-poc/blob/main/ai-poc/docs/architecture-overview.md) for diagrams and more detail.

---

