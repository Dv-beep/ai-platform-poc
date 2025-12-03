# AI Knowledge Platform – RAG

This repository contains a self-hosted AI Knowledge Platform built around **Retrieval-Augmented Generation (RAG)**.

---

## Architecture Diagram

<p align="center">
  <img src="ai-poc/docs/screenshots/architecture.png" width="700"/>
</p>

The goal of this project is to provide a secure, internal-only AI assistant that can answer questions using an organization’s own knowledge base (SOPs, policies, internal docs) without sending data to external APIs.

---

## High-Level Overview

**Core idea:**  
Upload or mount internal documents → index them into a vector database → query them through a RAG API → interact via a chat UI.

**Tech stack (example – adjust as needed):**

- **LLM Runtime:** Ollama (local models, e.g. `llama3`, `phi-4`, etc.)
- **Chat UI:** Open WebUI
- **Vector DB:** ChromaDB
- **RAG API:** FastAPI service that:
  - accepts a user query  
  - retrieves relevant docs from ChromaDB  
  - builds a grounded prompt  
  - calls Ollama and returns an answer + sources
- **Indexer Service:** Python service that:
  - reads documents from a mounted KB directory  
  - chunks, embeds, and writes to ChromaDB
- **Reverse Proxy / TLS:** Caddy
- **Orchestration:** Docker Compose

---

## Architecture

### Components

1. **Open WebUI**
   - Frontend chat experience for users
   - Sends RAG requests to the `rag-api` service

2. **RAG API (`services/rag-api`)**
   - REST API for RAG queries
   - Endpoints like:
     - `POST /api/rag/query` – ask a question with optional filters
     - `GET /api/health` – health check
   - Orchestrates:
     - search in ChromaDB
     - building the final prompt
     - calling Ollama
     - formatting the response + citations

3. **ChromaDB**
   - Stores vector embeddings for KB documents
   - Collections organized by namespace (e.g. `kb_sops`, `policies`, `howto`)

4. **KB Indexer (`services/kb-indexer`)**
   - Ingests files from a directory (e.g. `kb-samples/`)
   - Normalizes and chunks content (PDF, DOCX, MD, etc.)
   - Uses a sentence-transformer / embedding model
   - Pushes embeddings + metadata into ChromaDB

5. **Ollama**
   - Runs local LLMs
   - Keeps all prompts and context on-prem

6. **Caddy / Reverse Proxy**
   - Terminates TLS
   - Routes traffic to:
     - `/` → Open WebUI
     - `/api/rag/` → RAG API

---

## Repository Structure

```text
ai-poc/
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
│   │   ├── main.py               
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
│   └── openwebui/
│       └── openwebui.yml
│
├── kb-samples/
│
└── scripts/

```

See [docs/arhitecture-overview.md](https://github.com/Dv-beep/ai-platform-poc/blob/main/ai-poc/docs/architecture-overview.md) for diagrams and more detail.

---

