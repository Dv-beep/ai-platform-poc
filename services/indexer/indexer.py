"""
KB Indexer

Scans one or more knowledge base root directories, reads supported files
(.txt, .md, .pdf, .docx), chunks them, and sends the content to a RAG API
/ingest endpoint for storage in a vector database (e.g. ChromaDB).
"""


import os
import hashlib
import json
from datetime import datetime, timezone
from typing import List, Dict, Optional, Set

import requests
from pypdf import PdfReader
from docx import Document
import pandas as pd  # CSV/Excel support

# Environment variables (set via docker-compose / .env)
KB_ROOTS_ENV = os.environ.get(
    "KB_ROOTS",
    "/kb/knowledgebase,/kb/sops,/kb/datasets",
)
RAG_API_URL = os.environ.get("RAG_API_URL", "http://rag-api:9000")
ADMIN_API_KEY = os.environ.get("ADMIN_API_KEY")  # API key for RAG admin endpoints

# Comma-separated list of roots inside the container
KB_ROOTS: List[str] = [p.strip() for p in KB_ROOTS_ENV.split(",") if p.strip()]

# IMPORTANT:
# Changing KB_ROOTS is treated as deleting an entire KB source.
# If a root is removed from KB_ROOTS, all its documents will be PURGED from Chroma,
# unless ALLOW_ROOT_REMOVAL=true is set in the environment.

# Simple file extensions
TEXT_EXTENSIONS = {".txt", ".md", ".markdown", ".log"}
PDF_EXTENSIONS = {".pdf"}
DOCX_EXTENSIONS = {".docx"}
CSV_EXTENSIONS = {".csv"}
EXCEL_EXTENSIONS = {".xlsx", ".xls", ".xlsm"}

# State file to remember hashes between runs (mounted from host)
STATE_FILE = "/app/index_state.json"

# Endpoint for pushing indexer status into the RAG API
INDEXER_STATUS_ENDPOINT = os.environ.get(
    "INDEXER_STATUS_ENDPOINT",
    f"{RAG_API_URL}/admin/indexer_status",
)


def log(msg: str) -> None:
    print(f"[INDEXER] {msg}", flush=True)


def report_indexer_status(
    last_run: Optional[str],
    last_error: Optional[str],
    kb_roots: List[str],
    files_seen: int,
    docs_indexed: int,
    deleted_docs: int,
) -> None:
    payload = {
        "last_run": last_run,
        "last_error": last_error,
        "kb_roots": kb_roots,
        "files_seen": files_seen,
        "docs_indexed": docs_indexed,
        "deleted_docs": deleted_docs,
    }

    headers = {
        "Content-Type": "application/json",
    }
    if ADMIN_API_KEY:
        headers["X-Admin-Key"] = ADMIN_API_KEY

    try:
        resp = requests.post(
            INDEXER_STATUS_ENDPOINT,
            json=payload,  # let requests handle JSON encoding
            headers=headers,
            timeout=10,
        )
        log(f"Indexer status report: {resp.status_code} {resp.text}")
    except Exception as e:
        log(f"Failed to report indexer status: {e}")


def file_sha256(path: str, chunk_size: int = 8192) -> str:
    """Return SHA-256 hash of a file."""
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for block in iter(lambda: f.read(chunk_size), b""):
            if not block:
                break
            h.update(block)
    return h.hexdigest()


def iso_utc_from_mtime(path: str) -> str:
    """Return file mtime as ISO8601 UTC string."""
    ts = os.stat(path).st_mtime
    dt = datetime.fromtimestamp(ts, tz=timezone.utc)
    return dt.isoformat().replace("+00:00", "Z")


def chunk_text(text: str, max_chars: int = 1500) -> List[str]:
    """Naive chunker: split text into ~max_chars segments on newline/space where possible."""
    text = text.strip()
    if not text:
        return []

    chunks: List[str] = []
    start = 0
    length = len(text)

    while start < length:
        end = min(start + max_chars, length)
        cut = end

        # Try to cut on newline or space near the end
        newline_pos = text.rfind("\n", start, end)
        space_pos = text.rfind(" ", start, end)

        if newline_pos != -1:
            cut = newline_pos + 1
        elif space_pos != -1:
            cut = space_pos + 1

        chunk = text[start:cut].strip()
        if chunk:
            chunks.append(chunk)

        start = cut

    return chunks


def read_text_file(path: str) -> str:
    """Read a plain text file as UTF-8 (best effort)."""
    with open(path, "r", encoding="utf-8", errors="ignore") as f:
        return f.read()


def read_pdf_file(path: str) -> str:
    """Extract text from a PDF using pypdf."""
    try:
        reader = PdfReader(path)
        texts = []
        for page in reader.pages:
            page_text = page.extract_text() or ""
            texts.append(page_text)
        return "\n".join(texts)
    except Exception as e:
        log(f"Error reading PDF {path}: {e}")
        return ""


def read_docx_file(path: str) -> str:
    """Extract text from a DOCX using python-docx."""
    try:
        doc = Document(path)
        return "\n".join(p.text for p in doc.paragraphs)
    except Exception as e:
        log(f"Error reading DOCX {path}: {e}")
        return ""


def read_csv_file(path: str) -> str:
    """
    Read a CSV via pandas and serialize to a text form
    that's friendly for embeddings: header row + rows, no index.
    """
    try:
        df = pd.read_csv(path)
        return df.to_csv(index=False)
    except Exception as e:
        log(f"Error reading CSV {path}: {e}")
        return ""


def read_excel_file(path: str) -> str:
    """
    Read an Excel file (all sheets) and serialize to text.
    Each sheet is prefixed so the LLM has context.
    """
    try:
        sheets = pd.read_excel(path, sheet_name=None)  # dict(sheet_name -> DataFrame)
        parts = []
        for sheet_name, df in sheets.items():
            sheet_text = df.to_csv(index=False)
            parts.append(f"### Sheet: {sheet_name}\n{sheet_text}")
        return "\n\n".join(parts)
    except Exception as e:
        log(f"Error reading Excel {path}: {e}")
        return ""


def should_index_file(path: str) -> bool:
    """Decide if a file should be indexed based on extension."""
    if not os.path.isfile(path):
        return False

    name = os.path.basename(path)
    if name.startswith("."):
        return False

    _, ext = os.path.splitext(name)
    ext = ext.lower()

    if ext in (
        TEXT_EXTENSIONS
        | PDF_EXTENSIONS
        | DOCX_EXTENSIONS
        | CSV_EXTENSIONS
        | EXCEL_EXTENSIONS
    ):
        return True

    return False


def read_file_as_text(path: str) -> str:
    """Route to the proper reader by extension."""
    _, ext = os.path.splitext(path)
    ext = ext.lower()

    if ext in TEXT_EXTENSIONS:
        return read_text_file(path)
    elif ext in PDF_EXTENSIONS:
        return read_pdf_file(path)
    elif ext in DOCX_EXTENSIONS:
        return read_docx_file(path)
    elif ext in CSV_EXTENSIONS:
        return read_csv_file(path)
    elif ext in EXCEL_EXTENSIONS:
        return read_excel_file(path)
    else:
        # Fallback: treat as text
        return read_text_file(path)


def build_document_id(root_label: str, full_path: str, root_path: str) -> str:
    """
    Build a stable document_id, e.g.:
      root_label = "sops"
      full_path  = "/kb/sops/chromadb_canary.txt"
      root_path  = "/kb/sops"
    => document_id = "sops/chromadb_canary.txt"
    """
    rel_path = os.path.relpath(full_path, start=root_path)
    rel_path = rel_path.replace(os.sep, "/")
    return f"{root_label}/{rel_path}"


def load_index_state() -> Dict[str, Dict[str, str]]:
    """Load the index state file (doc_hash per document_id)."""
    if not os.path.exists(STATE_FILE):
        return {}
    try:
        with open(STATE_FILE, "r") as f:
            return json.load(f)
    except Exception as e:
        log(f"Warning: could not read state file; starting fresh. Error: {e}")
        return {}


def save_index_state(state: Dict[str, Dict[str, str]]) -> None:
    """Save updated index state file."""
    with open(STATE_FILE, "w") as f:
        json.dump(state, f, indent=2)


def ingest_file(
    root_label: str,
    root_path: str,
    full_path: str,
    state: Dict[str, Dict[str, str]],
    seen_ids: Set[str],
) -> bool:
    """
    Read, chunk, and send a single file to the RAG API /ingest endpoint.
    Returns True if the file was successfully indexed (2xx from API), else False.
    """
    if not should_index_file(full_path):
        log(f"Skipping unsupported or non-text file: {full_path}")
        return False

    name = os.path.basename(full_path)
    _, ext = os.path.splitext(name)
    ext = ext.lower()

    document_id = build_document_id(root_label, full_path, root_path)

    # Mark that we saw this doc_id on disk this run
    seen_ids.add(document_id)

    doc_hash = file_sha256(full_path)
    last_modified = iso_utc_from_mtime(full_path)

    if document_id in state and state[document_id].get("doc_hash") == doc_hash:
        log(f"Skipping unchanged file: {full_path}")
        return False

    log(f"Indexing file: {full_path}")

    raw_text = read_file_as_text(full_path)
    text_chunks = chunk_text(raw_text, max_chars=1500)

    if not text_chunks:
        log(f"No content to index in file: {full_path}")
        return False

    chunks = []
    total_chunks = len(text_chunks)
    for idx, chunk_text_block in enumerate(text_chunks):
        chunk_id = f"{document_id}#chunk-{idx}"
        chunks.append(
            {
                "id": chunk_id,
                "text": chunk_text_block,
                "metadata": {
                    "path": name,
                    "source": root_label,
                    "file_type": ext.lstrip("."),
                    "chunk_index": idx,
                    "chunk_count": total_chunks,
                    "document_id": document_id,
                    "source_path": full_path,
                },
            }
        )

    payload = {
        "document_id": document_id,
        "doc_hash": doc_hash,
        "last_modified": last_modified,
        "chunks": chunks,
    }

    try:
        headers = {"Content-Type": "application/json"}
        if ADMIN_API_KEY:
            headers["X-Admin-Key"] = ADMIN_API_KEY

        resp = requests.post(
            f"{RAG_API_URL}/ingest",
            headers=headers,
            data=json.dumps(payload),
            timeout=120,
        )
        log(f"Ingest response for {document_id}: {resp.status_code} {resp.text}")

        if 200 <= resp.status_code < 300:
            state[document_id] = {
                "doc_hash": doc_hash,
                "last_modified": last_modified,
            }
            return True

    except Exception as e:
        log(f"Error ingesting {document_id}: {e}")

    return False


def index_root(
    root_path: str,
    state: Dict[str, Dict[str, str]],
    seen_ids: Set[str],
) -> int:
    """Walk a single KB root and ingest all indexable files. Returns # of indexed docs."""
    root_label = os.path.basename(root_path.rstrip("/"))
    if not os.path.isdir(root_path):
        log(f"Root path does not exist or is not a directory: {root_path}")
        return 0

    log(f"Scanning root '{root_label}' at {root_path}")

    indexed_count = 0
    for dirpath, dirnames, filenames in os.walk(root_path):
        # Skip hidden directories
        dirnames[:] = [d for d in dirnames if not d.startswith(".")]
        for filename in filenames:
            full_path = os.path.join(dirpath, filename)
            if ingest_file(root_label, root_path, full_path, state, seen_ids):
                indexed_count += 1

    return indexed_count


def get_collection_doc_count() -> Optional[int]:
    """
    Ask RAG API for the current Chroma document count via /admin/status.
    Chroma empty → 0
    Chroma unreachable → None
    Chroma has data → non-zero
    """
    try:
        headers = {}
        if ADMIN_API_KEY:
            headers["X-Admin-Key"] = ADMIN_API_KEY

        resp = requests.get(f"{RAG_API_URL}/admin/status", headers=headers, timeout=10)
        resp.raise_for_status()
        data = resp.json()
        return int(data.get("document_count", 0))
    except Exception as e:
        log(f"Warning: could not fetch collection stats: {e}")
        return None


def delete_document_from_rag(document_id: str) -> bool:
    """
    Attempt to delete a document from Chroma via the RAG API.
    Returns True if deletion succeeded (2xx), False otherwise.
    """
    try:
        headers = {"Content-Type": "application/json"}
        if ADMIN_API_KEY:
            headers["X-Admin-Key"] = ADMIN_API_KEY

        resp = requests.post(
            f"{RAG_API_URL}/delete_document",
            headers=headers,
            data=json.dumps({"document_id": document_id}),
            timeout=30,
        )
        if 200 <= resp.status_code < 300:
            log(f"Delete response for {document_id}: {resp.status_code} {resp.text}")
            return True
        else:
            log(
                f"Delete failed for {document_id}: "
                f"{resp.status_code} {resp.text}"
            )
            return False
    except Exception as e:
        log(f"Error deleting {document_id} from RAG API: {e}")
        return False


def is_mount_healthy(path: str) -> bool:
    """
    Return True if:
      1) Path exists and is a directory
      2) Path is an active mount point
      3) Directory is not empty (SMB sometimes mounts but returns empty)
    """
    if not os.path.isdir(path):
        return False

    if not os.path.ismount(path):
        return False

    try:
        entries = os.listdir(path)
        return len(entries) > 0
    except Exception:
        return False


def main() -> None:
    log(f"KB_ROOTS: {KB_ROOTS}")
    log(f"RAG_API_URL: {RAG_API_URL}")

    # ---- Mount Health Check: Prevent Accidental Wipes ----
    unhealthy_mounts = [root for root in KB_ROOTS if not is_mount_healthy(root)]

    if unhealthy_mounts:
        log("======================================================")
        log("   KB ROOT MOUNT FAILURE — ABORTING INDEXER RUN")
        log("------------------------------------------------------")
        log(f"The following KB roots are not healthy/mounted: {unhealthy_mounts}")
        log("Skipping indexing to avoid accidental deletions.")
        log("======================================================")
        return

    collection_doc_count = get_collection_doc_count()
    kb_has_files = any(
        os.path.isdir(root) and any(files for _, _, files in os.walk(root))
        for root in KB_ROOTS
    )

    state = load_index_state()
    seen_ids: Set[str] = set()

    # Reset state if Chroma is empty but KB has files
    if collection_doc_count == 0 and kb_has_files and state:
        log(
            "Chroma collection is empty but KB has files; "
            "resetting index_state.json for full reindex."
        )
        state = {}

    # Index all roots, track what exists on disk
    total_indexed_docs = 0
    for root in KB_ROOTS:
        total_indexed_docs += index_root(root, state, seen_ids)

    # Anything in state but not seen this run = deleted from KB → candidate for delete
    existing_ids = set(state.keys())
    deleted_ids = existing_ids - seen_ids

    # ---- KB ROOT REMOVAL GUARD ----
    # Prevent accidental purge if a KB root is removed from KB_ROOTS config
    ALLOW_ROOT_REMOVAL = (
        os.environ.get("ALLOW_ROOT_REMOVAL", "false").lower() == "true"
    )

    root_labels_in_state = {doc_id.split("/", 1)[0] for doc_id in existing_ids}
    current_root_labels = {os.path.basename(r.rstrip("/")) for r in KB_ROOTS}
    removed_roots = root_labels_in_state - current_root_labels

    if removed_roots and not ALLOW_ROOT_REMOVAL:
        log("======================================================")
        log("   KB ROOT REMOVAL DETECTED — ABORTING DELETION PASS")
        log("------------------------------------------------------")
        log(f"Roots removed from KB_ROOTS: {removed_roots}")
        log("To allow this deletion, set ALLOW_ROOT_REMOVAL=true")
        log("Skipping indexer deletion pass to prevent data loss.")
        log("======================================================")
        perform_deletes = False
    else:
        perform_deletes = True

    # ---- Perform deletions if allowed ----
    deleted_count = 0
    if deleted_ids and perform_deletes:
        log(
            f"Detected {len(deleted_ids)} deleted documents; "
            "removing from Chroma and state."
        )
        for doc_id in deleted_ids:
            if delete_document_from_rag(doc_id):
                state.pop(doc_id, None)
                deleted_count += 1
    elif deleted_ids and not perform_deletes:
        log(
            f"Detected {len(deleted_ids)} deleted documents, "
            "but skipping deletion due to KB root removal guard."
        )

    save_index_state(state)
    log("Indexing completed.")

    last_run = datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")

    report_indexer_status(
        last_run=last_run,
        last_error=None,
        kb_roots=KB_ROOTS,
        files_seen=len(seen_ids),
        docs_indexed=total_indexed_docs,
        deleted_docs=deleted_count if perform_deletes else 0,
    )


if __name__ == "__main__":
    main()
