# AI Knowledge Platform – RAG Proof of Concept

This repository contains a self-hosted AI Knowledge Platform built around **Retrieval-Augmented Generation (RAG)**.

The goal of this project is to provide a secure, internal-only AI assistant that can answer questions using an organization’s own knowledge base (SOPs, policies, internal docs) without sending data to external APIs.

---

## 🔍 High-Level Overview

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
- **Reverse Proxy / TLS:** Caddy (or Nginx)
- **Orchestration:** Docker Compose

---

## 🧱 Architecture

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
   - Terminates TLS (if configured)
   - Routes traffic to:
     - `/` → Open WebUI
     - `/api/rag/` → RAG API

---

## 🗂️ Repository Structure

```text
.
├── README.md
├── docs/
│   ├── architecture-overview.md
│   ├── rag-sequence-diagram.md
│   ├── screenshots/
│   │   ├── openwebui-home.png
│   │   └── rag-chat-example.png
├── deploy/
│   ├── docker-compose.yml
│   ├── .env.example
│   ├── caddy/
│   │   └── Caddyfile
│   ├── openwebui/
│   │   └── openwebui.yaml
│   └── chromadb/
│       └── chromadb.config.yaml
├── services/
│   ├── rag-api/
│   └── kb-indexer/
├── kb-samples/
└── scripts/
```
See docs/architecture-overview.md for diagrams and more detail.

---

🚀 Getting Started

1. Prerequisites
	•	Docker & Docker Compose
	•	(Optional) NVIDIA GPU drivers + CUDA for GPU acceleration with Ollama

2. Clone the repo

git clone https://github.com/<your-username>/ai-platform-poc.git
cd ai-platform-poc

3. Configure environment

Copy the example env file and adjust values:
cp deploy/.env.example deploy/.env   

Configure:
	•	OLLAMA_BASE_URL
	•	CHROMA_HOST / CHROMA_PORT
	•	RAG_API_PORT
	•	OPENWEBUI_PORT
	•	Any auth/API keys if you add them later






