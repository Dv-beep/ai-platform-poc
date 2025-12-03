# **AI-POC: Retrieval-Augmented Generation (RAG) System**

This project implements an on-premise Retrieval-Augmented Generation (RAG) pipeline for securely querying an internal knowledge bases (KBs/SOPs). All data, embeddings, and LLM inference remain fully inside the network—no cloud services or external APIs.

The system is built using OpenWebUI, a custom RAG API, ChromaDB, Ollama, and a document indexer, all running in an isolated containerized environment.

---

## **Architecture Overview**

The AI-POC pipeline retrieves relevant internal content and augments the LLM’s response using ChromaDB-stored KB/SOP embeddings.

```
                    ┌─────────────────────────┐
                    │       Users             │
                    └────────────┬────────────┘
                                 │  HTTPS
                                 ▼
                        ┌────────────────┐
                        │  OpenWebUI     │
                        │ (Chat Client)  │
                        └───────┬────────┘
                                │ RAG Tool Call
                                ▼
                    ┌──────────────────────────┐
                    │        RAG API           │
                    │  - Query Orchestration   │
                    │  - Prompt Builder        │
                    └─────────┬─────┬──────────┘
                              │     │
        ┌─────────────────────┘     └──────────────────────┐
        │                                                   │
        ▼                                                   ▼
┌──────────────────┐                              ┌──────────────────┐
│    ChromaDB      │                              │     Ollama       │
│ (Vector Store)   │                              │  (Local LLM)     │
└──────────────────┘                              └──────────────────┘

                       ▼
                 Final Answer
```

---

## **Data Ingestion & Indexing Workflow**

Internal KB & SOP directories on the Windows file server are mounted into the Linux host and processed by the indexer container:

```
CIFS File Shares
   ├── //domain.com/.../KB
   └── //domaiin.com/.../SOP
            │
            ▼
     Linux Host Mounts
     /mnt/KB
     /mnt/SOPs
            │
            ▼
   kb-indexer Container
   - Reads PDFs / DOCX
   - Extracts text
   - Chunks documents
   - Pushes embeddings → ChromaDB
            │
            ▼
     ChromaDB Collection
          collection_name
```

This ensures all documentation is searchable and query-ready.

---

## **RAG Query Flow (Step-by-Step)**

1. **User asks a question** in OpenWebUI.
2. OpenWebUI’s RAG tool sends the question → **RAG API**.
3. RAG API queries **ChromaDB** (collection: `collection_name`) to retrieve the top-K relevant chunks.
4. RAG API inserts those chunks into a structured prompt.
5. RAG API sends the prompt to **Ollama**, which performs LLM inference on-prem.
6. The LLM generates the final answer with context and citations.
7. OpenWebUI displays the answer to the user.

All retrieval and inference operations occur internally.

---

## **🧩 Core Components**

### **1. OpenWebUI**

* Main chat interface for users
* Supports RAG tool integration
* Hosted locally and isolated from external networks

### **2. RAG API**

* Python/FastAPI microservice
* Handles:

  * retrieval → prompt building → LLM inference
  * formatting prompt templates
  * managing context windows

### **3. ChromaDB**

* Vector database storing embeddings
* Collection: `collection_name`
* Accessible only on internal Docker networks

### **4. Ollama**

* Local LLM runtime (GPU-enabled)
* Supports models such as:

  * `llama2:7b`
  * `phi4-reasoning:14b`
  * `mistral`
* Ensures data never leaves the internal environment

### **5. kb-indexer**

* Scans mounted KB/SOP directories
* Converts PDF/DOCX → text
* Chunks and embeds
* Pushes to ChromaDB

---

## **Security & Isolation**

* Fully on-prem; no external APIs
* CIFS mounts set to **read-only** from Windows file server
* Docker network isolation prevents cross-container exposure
* Optional future TLS termination with Caddy
* Suitable for HIPAA/IRB data environments

---

## **Optional: API Gateway Enhancement**

If multiple systems will use the RAG pipeline (OpenWebUI, web portals, n8n, Slack bots), an API Gateway can wrap the RAG API:

```
              ┌──────────────┐
              │ API Gateway  │
              └───────┬──────┘
                      ▼
                 RAG API
           /query /embed /health
```

Provides:

* Authentication
* Rate limiting
* Logging
* Standardized access for multiple apps

---

## **Summary**

The AI-POC’s RAG implementation provides a fully internal, secure, GPU-accelerated knowledge retrieval system. It integrates:

* On-prem file shares
* Automated document ingestion
* ChromaDB vector search
* Local LLM inference via Ollama
* OpenWebUI as a friendly interface

This architecture lays the foundation for future enterprise-grade internal AI systems, including APIs, Slack integrations, research tools, automation, and more.
