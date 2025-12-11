ai-platform-poc/
├── README.md
├── LICENSE
├── .env.example
├── .gitignore
│
├── docs/
│   ├── architecture/
│   │   ├── architecture-overview.md
│   │   └── rag-sequence-diagram.md
│   ├── operations/
│   │   ├── stack-deploy.md          # how to bring up/down stacks (Portainer + docker compose)
│   │   ├── kb-ingestion-playbook.md # how to add/update KB roots, metadata schema, etc.
│   │   ├── troubleshooting.md       # common errors (mounts, GPU, Chroma, indexer, rag-api)
│   ├── prompts/
│   │   ├── openwebui-system-prompt.md
│   │   └── rag-template.md          # the {system_prompt}/{context}/{history}/{prompt} template
│   ├── eval/
│   │   ├── rag-eval-overview.md     # how to run/interpret RAG eval
│   │   └── eval-cases-examples.md
│   └── screenshots/
│       ├── architecture.png
│       ├── rag-connection-tool.png
│       └── portainer-stack.png
│
├── services/
│   ├── rag-api/
│   │   ├── app/
│   │   │   ├── __init__.py
│   │   │   ├── main.py              # FastAPI `app` + startup wiring
│   │   │   ├── api/                 # endpoints split cleanly for README snippets
│   │   │   │   ├── query.py         # /query
│   │   │   │   ├── ingest.py        # /ingest
│   │   │   │   └── admin.py         # /admin/status, /admin/metrics, etc.
│   │   │   ├── core/
│   │   │   │   ├── config.py        # env parsing, collection name, model config, etc.
│   │   │   │   └── logging.py       # structured logging helpers
│   │   │   ├── models/
│   │   │   │   ├── requests.py      # Pydantic request models (QueryRequest, IngestRequest, etc.)
│   │   │   │   └── responses.py     # Pydantic response models (QueryResponse, AdminStatusResponse, etc.)
│   │   │   └── services/
│   │   │       ├── chroma_client.py # wrapper around Chroma collection
│   │   │       └── embeddings.py    # call out to embedding model if/when needed
│   │   ├── tests/
│   │   │   ├── test_query_endpoint.py
│   │   │   ├── test_ingest_endpoint.py
│   │   │   └── test_admin_status.py
│   │   ├── Dockerfile
│   │   └── requirements.txt
│   │
│   ├── indexer/
│   │   ├── app/
│   │   │   ├── __init__.py
│   │   │   ├── indexer.py           # entrypoint, main loop
│   │   │   ├── config.py            # KB_ROOTS, RAG_API_URL, hash settings, polling interval
│   │   │   ├── models.py            # dataclasses/Pydantic for IndexRunState, DocumentMetadata, etc.
│   │   │   ├── filesystem.py        # walk roots, detect changes, hashing
│   │   │   ├── ingestion_client.py  # thin client for rag-api /ingest
│   │   │   └── dedupe.py            # semantic dedupe / hash-based dedupe helpers
│   │   ├── tests/
│   │   │   ├── test_hashing.py
│   │   │   ├── test_metadata_extraction.py
│   │   │   └── test_ingest_payload.py
│   │   ├── Dockerfile
│   │   └── requirements.txt
│   │
│   ├── chromadb/
│   │   ├── Dockerfile              # if/when you customize the Chroma image
│   │   └── config/                 # chroma config, persistence volume mapping docs
│   │       └── chroma-example.toml # optional
│   │
│   └── mlflow/                     # placeholder for Clayton’s stack if it lands here
│       ├── Dockerfile
│       └── mlflow-config-example.yaml
│
├── deploy/
│   ├── compose/
│   │   ├── stack-ai-poc.yml        # main stack: rag-api + indexer + chroma
│   │   ├── stack-openwebui.yml     # openwebui + Ollama external or host
│   │   ├── stack-mlops.yml         # optional: MLflow + friends
│   │   └── stack-all-in-one.yml    # convenience “bring up everything” stack
│   ├── caddy/
│   │   └── Caddyfile
│   ├── traefik/                    # if you go API gateway / auth later
│   │   └── traefik.yml
│   └── portainer/
│       └── portainer-stack-note.md # how to import the stack in Portainer at 10.200.2.200:9443
│
├── kb/
│   ├── samples/
│   │   ├── knowledgebase/
│   │   │   ├── Laptop Password Reset Procedure.docx
│   │   │   └── Department Name Abbreviations.xlsx
│   │   ├── sops/
│   │   │   ├── Compromised_or_Risky_Account_SOP.docx
│   │   │   └── Users_Cannot_Remotely_Connect_SOP.docx
│   │   └── datasets/
│   │       └── sample-dataset.xlsx
│   ├── templates/
│   │   ├── sop-template.docx       # the canonical SOP template you’re using
│   │   └── metadata-schema.json    # agreed metadata fields for indexing
│   └── README.md                   # how to structure KB roots for this project
│
├── eval/
│   ├── eval_cases.yaml             # the RAG eval cases you were asking about
│   ├── run_eval.py                 # CLI runner against rag-api /query
│   └── results/
│       └── sample-run-2025-12-xx.json
│
├── scripts/
│   ├── dev/
│   │   ├── start-ai-poc.sh         # docker compose up ai-poc
│   │   ├── stop-ai-poc.sh
│   │   └── tail-logs.sh            # helper to tail rag-api/indexer logs
│   ├── maintenance/
│   │   ├── backup-chroma.sh
│   │   └── check-smb-mounts.sh
│   └── tooling/
│       ├── format-python.sh        # black/isort/ruff if you add them
│       └── healthcheck.sh          # calls /admin/status from rag-api
│
└── .github/
    └── workflows/
        ├── ci-python.yml           # lint + tests for rag-api & indexer
        └── docker-build.yml        # optional: build images on main
