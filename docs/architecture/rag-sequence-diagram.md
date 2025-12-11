# RAG Sequence Diagrams

This document shows how the AI POC handles:

1. **Indexing** internal knowledge base files into ChromaDB.
2. **Serving RAG queries** from OpenWebUI through the RAG API and ChromaDB into the LLM.

---

## High-Level Summary

- **ETL Pipeline**
    SMB File Shares -> KB Indexer -> Embeddings -> ChromaDB (collection).
- **Query/Response**
    User -> OpenWebUI -> LLM -> External Server Tool -> RAG API -> ChromaDB -> Ollama -> Answer back to User.

This keeps all KB/SOP data internal while still giving the model rich, contextual access to enterprise knowledge through RAG.

---

## 1. Indexing Flow (Enterprise Documents → KB Indexer → ChromaDB)

This flow runs out-of-band via the `kb-indexer` container. It crawls internal SMB shares, chunks documents, and pushes embeddings into ChromaDB.

```mermaid
sequenceDiagram
    autonumber
    participant FS as File Share<br/>(KB / SOPs)
    participant IDX as KB Indexer<br/>(indexer.py)
    participant EMB as Embedding Model<br/>(SentenceTransformers)
    participant C as ChromaDB Server

    Note over IDX,FS: Index job started (manual or scheduled)

    IDX->>FS: List files in mounted KB/SOP directories
    loop For each document
        IDX->>FS: Read document (PDF, DOCX, etc.)
        IDX->>IDX: Clean & chunk content<br/>(metadata: path, type, tags)
        IDX->>EMB: Generate embeddings for chunks
        EMB-->>IDX: Return vector embeddings

        IDX->>C: Upsert documents + embeddings<br/>into collection (e.g. enterprise_collection)
        C-->>IDX: Confirm write (ids / stats)
    end

    Note over IDX,C: ChromaDB now holds up-to-date<br/>vector index of internal KB/SOPs
```

**Key points:**

- **File Share:** Internal SMB mounts
- **KB Indexer:** Python script/container that:
    - Reads files, normalizes text.
    - Chunks content and attaches metadata (path, doc type, version, date-time).
    - Calls the embedding model and upserts into **ChromaDB**.
- **ChromaDB:** Central vector store serving the *enterprise_collection*.

---

## 2. Query Flow (OpenWebUI → RAG API → ChromaDB → LLM)

This flow shows what happens when a user asks a question in OpenWebUI and the model uses the External Server tool (backed by the RAG API).
```mermaid
sequenceDiagram
    autonumber
    participant U as User
    participant W as OpenWebUI
    participant L as LLM<br/>(Ollama)
    participant T as RAG Tool<br/>(Tool Server)
    participant R as RAG API<br/>(FastAPI)
    participant C as ChromaDB
    participant FS as File Share<br/>(KB / SOPs)

    U->>W: Enters question about internal KB/SOP
    W->>L: Send chat request with tool schema<br/>(includes RAG tool)

    Note over L,W: LLM decides it needs KB context<br/>and calls the tool

    L-->>W: Tool call request<br/>(e.g. { "tool": "RAG tool", "question": "..." })
    W->>T: Forward tool call to tool server
    T->>R: HTTP POST /query<br/>{ question, filters }

    Note over R: RAG pipeline execution

    R->>C: Query collection for top-k relevant chunks
    C-->>R: Return chunks + metadata<br/>(content, titles, file paths)

    R->>R: Build RAG prompt template<br/>(instructions + context + question)
    R->>L: Call LLM via Ollama API<br/>(prompt with retrieved context)
    L-->>R: Answer grounded in KB + citations

    R-->>T: Tool response payload<br/>{ answer, sources }
    T-->>W: Pass tool result back to OpenWebUI
    W->>L: Provide tool result as context<br/>for final model response
    L-->>W: Final natural-language answer
    W-->>U: Display answer + optional sources/links
```
**Key points**

- **User -> OpenWebUI**
    The user just chats normally. OpenWebUI sends the prompt to the LLM with the External Server tool available.
- **LLM -> Tool Call**
    The model decides it needs organizational knowledge and triggers the External Server tool, which calls the **RAG API**.
- **RAG API**
    - Accepts the question
    - Queries **ChromaDB** for the most relevant chunks.
    - Constructs a RAG prompt (system instructions + retrieved chunks + user question).
    - Calls **Ollama** to generate an answer grounded in the Collection.
    - Returns both the **answer** and **sources** (file paths / titles /snippet IDs).
- **OpenWebUI Final Answer**
    The tool response is injected back into the LLM's context so it can:
    - Explain the answer in natural language.
    - Surface citations back to the orginal documents on the file share.
