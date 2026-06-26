# Investment Research Analyst Agent — Technical Documentation

## 1. Overview

A local-first, multi-agent AI system that ingests financial documents (annual reports, earnings transcripts, filings) and answers natural-language investment research questions. The system orchestrates five specialized LLM-powered agents — Planner, Researcher, Risk Analyst, Writer, and Reviewer — through a pipeline that retrieves evidence from a vector database, enriches it with live market data via MCP tools, and produces a structured Markdown investment report.

**Key characteristics:**
- Entirely local — no cloud dependency. Uses Ollama-hosted models.
- Background document indexing with chunk-level progress reporting.
- Streaming research timeline with live agent step visibility.
- Cancellable and async research workflows.
- Dual observability: MLflow (opt-in) and Langfuse (opt-in, self-hosted or cloud).
- Built-in MCP (Model Context Protocol) server exposing financial data tools that agents consume alongside document evidence.

---

## 2. System Architecture

```
                    ┌─────────────────────────┐
                    │    Browser (HTML/CSS/JS)│
                    │ SSE streaming, polling  │
                    └───────────┬─────────────┘
                                │ HTTP / SSE
                                ▼
                ┌─────────────────────────────────┐
                │      FastAPI (Uvicorn)          │
                │ api/main.py — 15 endpoints      │
                │ Jinja2Templates, StaticFiles    │
                └───────────────┬─────────────────┘
                                │
          ┌─────────────────────┼─────────────────────┐
          │                     │                     │
          ▼                     ▼                     ▼
   ┌──────────────┐   ┌────────────────┐   ┌──────────────────┐
   │ Agent System │   │ MCP Client     │   │ Background       │
   │ 5 agents     │   │ stdio subproc  │   │ Indexer Threads  │
   │ pipeline     │   │ financial tools│   │ Document→Chunks→ │
   │ streaming    │   │ 4 tools        │   │ Embed→Qdrant     │
   └──────┬───────┘   └───────┬────────┘   └────────┬─────────┘
          │                   │                     │
          ▼                   ▼                     ▼
   ┌──────────────┐   ┌──────────────┐   ┌──────────────────┐
   │  Ollama API  │   │  MCP Server  │   │  Qdrant Vector DB│
   │ mistral:7b   │   │ stdio server │   │ investment_docs  │
   │ nomic-embed  │   │ 4 tools      │   │cosine similarity │
   └──────────────┘   └──────────────┘   └──────────────────┘
          │                                              │
          └──────────────┬───────────────────────────────┘
                         ▼
               ┌──────────────────┐
               │   PostgreSQL     │
               │ research_runs    │
               │ documents        │
               │ findings, reports│
               └──────────────────┘
```

### Layer Description

| Layer | Technology | Responsibility |
|---|---|---|
| **Presentation** | HTML, CSS, JavaScript | Single-page UI with SSE streaming, 3s/10s polling, collapsible sections, live agent timeline |
| **API** | FastAPI (Python 3.12) | REST endpoints for CRUD, SSE streaming, health monitoring. Serves static files and Jinja2 templates. |
| **Agents** | 5 Ollama-backed agents | Planner, Researcher, Risk Analyst, Writer, Reviewer — each with a dedicated system prompt and JSON output schema |
| **LLM** | Ollama (`/api/generate`) | Mistral:7b (primary), Gemma4:12b (fallback). Temperature 0.3, context 8192. |
| **Embeddings** | Ollama (`/api/embed` or `/api/embeddings`) | Nomic-embed-text (primary) with fallback chain through all-minilm, mxbai-embed-large |
| **Vector Store** | Qdrant | Cosine similarity search on 768-dimension embeddings. Collection: `investment_docs` |
| **Relational Store** | PostgreSQL 16 | Research runs, documents, findings, reports, evaluation metrics |
| **MCP** | Python `mcp` SDK + stdio transport | Server exposes 4 financial tools; client connects automatically in background thread |
| **Observability** | MLflow (opt-in) + Langfuse (opt-in) | LLM calls, agent steps, embedding calls, research runs logged as traces/spans/generations |

---

## 3. Component Deep Dive

### 3.1 Agent System (`api/agents/`)

All agents accept optional `on_llm_start` and `on_llm_finish` callbacks for streaming/tracking integration. Every agent calls `call_llm()` with a system prompt that forces JSON output, then parses the response.

#### 3.1.1 Planner Agent (`planner.py`)

- **Input:** User's natural-language research question (string)
- **Output:** `list[str]` — array of specific research tasks
- **Prompt template:** `PLANNER_PROMPT`
- **Parse strategy:** `json.loads()`, fallback to newline splitting, final fallback to default task
- **Example output:** `["Analyze profitability", "Analyze revenue growth", "Analyze capital strength", ...]`

#### 3.1.2 Researcher Agent (`researcher.py`)

- **Input:** Single task string from Planner
- **Output:** `dict` with keys `topic`, `summary`, `citations`
- **Evidence retrieval:**
  1. Embed the task via `get_embedding()`
  2. Query Qdrant via `QdrantSearch.search(vector, top_k=5)`
  3. Extract company names from task text
  4. Call MCP tools (`get_company_info`, `get_peers`, `get_stock_ticker`) for up to 2 matched companies
- **Prompt template:** `RESEARCHER_PROMPT` — includes evidence from documents + live market data
- **Company recognition list:** 18 hardcoded financial institution and tech company names

#### 3.1.3 Risk Analyst Agent (`risk_analyst.py`)

- **Input:** `list[dict]` — all findings from the Researcher
- **Output:** `list[dict]` — each with `risk_type`, `description`, `severity` (high/medium/low)
- **Risk categories:** Regulatory, Market, Interest-rate, Credit
- **Prompt template:** `RISK_ANALYST_PROMPT`

#### 3.1.4 Writer Agent (`writer.py`)

- **Input:** Original question + findings list + risk assessment list
- **Output:** `str` — full Markdown investment report
- **Report sections:** Executive Summary, Company Overview, Financial Analysis, Strategic Analysis, Risk Analysis, Investment Thesis, Conclusion
- **Prompt template:** `WRITER_PROMPT`

#### 3.1.5 Reviewer Agent (`reviewer.py`)

- **Input:** Draft report text (truncated to 3000 chars)
- **Output:** `dict` with `approved` (bool), `comments` (list[str]), `revision_requests` (list[str])
- **Review criteria:** Missing sections, unsupported conclusions, lack of evidence, overall quality
- **Prompt template:** `REVIEWER_PROMPT`
- **Integration:** The workflow runs up to 3 review cycles (2 revision rounds)

### 3.2 LLM Integration (`api/utils/llm.py`)

#### `call_llm()` — Core LLM Invocation

```
call_llm(prompt, system=None, model=None, on_start=None, on_finish=None) -> str
```

**Execution flow:**
1. Determine primary model (`model` parameter or `LLM_MODEL` from config)
2. Determine fallback model (`FALLBACK_LLM_MODEL`)
3. For each model (primary, then fallback if available):
   - Build payload: `{"model": m, "prompt": prompt, "stream": false, "options": {"temperature": 0.3, "num_ctx": 8192}}`
   - Optionally include `"system"` key
   - POST to `{OLLAMA_BASE_URL}/api/generate`
   - On success: extract `response` field, calculate duration from `total_duration` (ns→s) or wall clock
   - On failure: log error, try next model
4. For each attempt: invoke `on_start(model, prompt_len)`, then `on_finish(model, response_len, duration)`
5. Track via MLflow `log_llm_call()` and Langfuse `log_generation()`

**Timeout:** `LLM_TIMEOUT` (default 3600s) — httpx timeout parameter.

**Context window:** 8192 tokens (`num_ctx`).

#### `get_embedding()` — Embedding Generation

```
get_embedding(text) -> list[float]  (768-dim)
```

**Fallback chain:**
1. `EMBEDDING_MODEL` (default `"nomic-embed-text"`)
2. `"nomic-embed-text"`
3. `"all-minilm:latest"`
4. `"mxbai-embed-large"`

For each model, `_try_embed()` first attempts `_post_embed_v2()` (Ollama `/api/embed` endpoint, payload `{"model": m, "input": text}`), then falls back to `_post_embed_v1()` (Ollama `/api/embeddings` endpoint, payload `{"model": m, "prompt": text}`).

**Final fallback:** Returns `[0.0] * 768` if all models fail.

### 3.3 Document Indexing (`api/utils/indexer.py`)

```
index_document(document_id)  →  spawns daemon thread → _index_worker(document_id)
```

**Worker flow:**

```
                                                  
┌──────────┐   ┌──────────┐   ┌───────────┐   ┌───────────┐   ┌──────────┐
│  sleep(1)│ → │ Load doc │ → │ Chunk     │ → │ Embed +   │ → │ status = │
│  (delay) │   │ from DB  │   │ (1000/200)│   │ Store in  │   │ "ready"  │
└──────────┘   └──────────┘   └───────────┘   │ Qdrant    │   └──────────┘
                                              └───────────┘
```

| Step | Detail |
|---|---|
| **Load** | `DocumentLoader.load(filepath)` determines format by extension: PDF → `PyPDFLoader`, DOCX → `Docx2txtLoader`, TXT → `TextLoader` |
| **Chunk** | `RecursiveCharacterTextSplitter(chunk_size=1000, chunk_overlap=200)` — LangChain's standard text splitter |
| **Embed** | `get_embedding(chunk_text)` per chunk with 768-dim output |
| **Store** | `QdrantSearch.store_embeddings(points)` — upserts each vector with payload `{text, filename, company, chunk_index}` |
| **Progress** | `processed_chunks` column incremented after each chunk — UI polls every 3s to show `"47 / 187"` |
| **Errors** | Up to 5 errors captured; `status` set to `"failed"` with `error_message` (truncated to 500 chars) |

### 3.4 Vector Database — Qdrant (`api/tools/qdrant_search.py`)

**Class:** `QdrantSearch`

**Connection:** `QdrantClient(url=QDRANT_URL)` — default `http://127.0.0.1:6333`

**Collection:** Automatically created on first use via `_ensure_collection()`:
- `VectorParams(size=768, distance=Distance.COSINE)`

| Operation | Method | Details |
|---|---|---|
| **Store** | `store_embeddings(points)` | Bulk upsert with `{id, vector, payload}` dicts. Uses `async` Qdrant client for the actual write. |
| **Search** | `search(vector, top_k=5)` | Cosine similarity search. Returns `{id, score, text, metadata}` per result. |
| **Delete** | `delete_by_filename(filename)` | `FilterSelector` with `MatchValue` on payload `filename` field. |

**Payload structure per stored point:**
```json
{
  "text": "chunk text (truncated to 2000 chars)",
  "filename": "RBC_2024_Annual_Report.pdf",
  "company": "RBC",
  "chunk_index": 42
}
```

### 3.5 Relational Database — PostgreSQL (`api/database.py`, `api/models/`)

**Connection:** `DATABASE_URL` — default `postgresql://invest:invest@localhost:5432/invest_research`

**User and database setup:**

```sql
-- Create the database (run as postgres superuser)
CREATE DATABASE invest_research;

-- Create the role with login permission
CREATE ROLE invest WITH LOGIN PASSWORD 'invest';

-- Grant all privileges on the database
GRANT ALL PRIVILEGES ON DATABASE invest_research TO invest;

-- Connect to invest_research and grant schema permissions
\c invest_research
GRANT ALL ON SCHEMA public TO invest;
GRANT ALL PRIVILEGES ON ALL TABLES IN SCHEMA public TO invest;
GRANT ALL PRIVILEGES ON ALL SEQUENCES IN SCHEMA public TO invest;
ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT ALL ON TABLES TO invest;
ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT ALL ON SEQUENCES TO invest;
```

The Docker Compose setup handles this automatically via environment variables:

```yaml
postgres:
  image: postgres:16
  environment:
    POSTGRES_DB: invest_research
    POSTGRES_USER: invest
    POSTGRES_PASSWORD: invest
```

**ORM:** SQLAlchemy 2.0 with `declarative_base()` and session management.

#### Schema

```sql
-- Table: documents
CREATE TABLE documents (
    id SERIAL PRIMARY KEY,
    filename VARCHAR NOT NULL,
    company VARCHAR,
    status VARCHAR DEFAULT 'pending',
    chunk_count INTEGER DEFAULT 0,
    processed_chunks INTEGER DEFAULT 0,
    error_message VARCHAR,
    uploaded_at TIMESTAMP DEFAULT NOW()
);

-- Table: research_runs
CREATE TABLE research_runs (
    id SERIAL PRIMARY KEY,
    question TEXT NOT NULL,
    status VARCHAR DEFAULT 'pending',
    created_at TIMESTAMP DEFAULT NOW()
);

-- Table: findings
CREATE TABLE findings (
    id SERIAL PRIMARY KEY,
    research_run_id INTEGER NOT NULL REFERENCES research_runs(id),
    topic VARCHAR NOT NULL,
    content TEXT
);

-- Table: reports
CREATE TABLE reports (
    id SERIAL PRIMARY KEY,
    research_run_id INTEGER NOT NULL REFERENCES research_runs(id),
    report_text TEXT,
    created_at TIMESTAMP DEFAULT NOW()
);

-- Table: evaluation_metrics
CREATE TABLE evaluation_metrics (
    id SERIAL PRIMARY KEY,
    research_run_id INTEGER NOT NULL REFERENCES research_runs(id),
    metric_name VARCHAR NOT NULL,
    metric_value INTEGER
);
```

**Status state machine:**

```
Documents:  pending → processing → ready
                                  → failed

Runs:       pending → running → completed
                              → failed
                              → cancelled
```

**Auto-migration:** `init_db()` in `api/database.py` creates all tables via `Base.metadata.create_all()` and resets any documents stuck in `processing` back to `pending`.

### 3.6 MCP Integration (`api/tools/`)

#### MCP Server (`mcp_server.py`)

- **Transport:** stdio (spawned as subprocess)
- **Protocol:** MCP (Model Context Protocol) via Python `mcp` SDK

**Tools exposed:**

| Tool | Parameters | Description | Data source |
|---|---|---|---|
| `get_stock_ticker` | `company_name: str` | Look up ticker symbol | Hardcoded `_TICKER_HINTS` map (~20 companies) |
| `get_company_info` | `company: str` | Company info + available document snippets | Qdrant scroll → aggregated per company |
| `get_peers` | `company: str` | Peer/competitor companies | Hardcoded `_PEER_MAP` (bank/tech peer groups) |
| `search_documents` | `query: str`, `top_k: int` (opt, default 5, max 20) | Semantic document search | Qdrant search |

On startup, the server scrolls ALL points from the Qdrant collection to build an in-memory index of companies.

#### MCP Client (`mcp_client.py`)

**Class:** `MCPClient`

- **Transport:** stdio subprocess: `python3 -m api.tools.mcp_server`
- **Architecture:** Runs its own `asyncio` event loop in a daemon thread
- **Session:** Persistent `ClientSession` with stdio `read`/`write` streams

| Method | Details |
|---|---|
| `start()` | Spawns subprocess, starts background thread with `_connect()`, waits 2s for initialization |
| `_connect()` | Creates `stdio_client()`, establishes session, lists available tools, then sleeps (keeps thread alive) |
| `list_tools()` | Returns cached tool list from initialization |
| `call_tool(name, args)` | `run_coroutine_threadsafe` on the background event loop. 30s timeout. Returns JSON string. |
| `is_ready()` | Boolean flag |

**Global singleton pattern:**
```python
_client: MCPClient | None = None
get_client() -> MCPClient    # creates on first call
call_tool(name, arguments)   # convenience wrapper
```

### 3.7 Research Workflow (`api/workflows/research_workflow.py`)

**Class:** `ResearchWorkflow`

**Orchestration pipeline (`_pipeline`):**

```
question
  │
  ▼
┌─────────────────────────────────────────────────────┐
│  PlannerAgent.run(question)                         │
│  → list[str] tasks                                  │
└─────────────────────────────────────────────────────┘
  │
  ▼ (for each task)
┌─────────────────────────────────────────────────────┐
│  ResearcherAgent.run(task)                          │
│  → QdrantSearch.search(embed(task))                 │
│  → MCP client enrichment (company info, peers)      │
│  → call_llm(RESEARCHER_PROMPT)                      │
│  → store_finding(run_id, topic, summary)            │
│  → dict {topic, summary, citations}                 │
└─────────────────────────────────────────────────────┘
  │
  ▼
┌─────────────────────────────────────────────────────┐
│  RiskAnalystAgent.run(findings)                     │
│  → call_llm(RISK_ANALYST_PROMPT)                    │
│  → list[dict] {risk_type, description, severity}    │
└─────────────────────────────────────────────────────┘
  │
  ▼
┌─────────────────────────────────────────────────────┐
│  WriterAgent.run(question, findings, risks)          │
│  → call_llm(WRITER_PROMPT)                          │
│  → str (Markdown report)                            │
└─────────────────────────────────────────────────────┘
  │
  ▼ (up to 3 cycles)
┌─────────────────────────────────────────────────────┐
│  ReviewerAgent.run(report)                          │
│  → call_llm(REVIEWER_PROMPT)                        │
│  → dict approved / comments / revision_requests     │
│                                                     │
│  if not approved: Writer rewrites (up to 2 revs)    │
│  if approved: break                                 │
└─────────────────────────────────────────────────────┘
  │
  ▼
┌─────────────────────────────────────────────────────┐
│  store_report(run_id, report)                       │
│  update_run_status(run_id, "completed")             │
│  store_metric(tasks_count, findings_count, cycles)  │
└─────────────────────────────────────────────────────┘
```

**Three execution modes:**

| Mode | Method | Mechanism | Returns |
|---|---|---|---|
| Synchronous | `run(question)` | Generator iteration discarding yields | `run_id` (after completion) |
| Async | `run_async(question)` | Daemon `threading.Thread` | `run_id` (immediately) |
| Streaming | `run_stream(question)` | Yields `(event_type, json_str)` tuples | Generator consumed by SSE |

**Cancellation:**
- Global `_cancelled_runs: set[int]` protected by `_cancel_lock`
- `cancel_run(run_id)` adds ID to set
- `is_cancelled(run_id)` checked before each agent step in `_check_cancelled()`
- `WorkflowCancelled` exception propagated through the pipeline
- Run status updated to `"cancelled"`; Langfuse trace ended; set cleaned up

**Streaming events:**

| Event type | When | Data |
|---|---|---|
| `config` | Start | `{"primary": "...", "fallback": "..."}` |
| `status` | Milestones | `"Planning research..."`, `"Planned 3 tasks"`, etc. |
| `agent_start` | Before each agent | `{"name": "Planner", "model": "mistral:7b"}` |
| `agent_done` | After each agent | `{"name": "Planner", "duration": 2.3, "llm": {"model": "...", "response_len": 150, "duration": 2.1}}` |
| `agent_error` | Agent exception | `{"name": "Planner", "error": "...", "duration": 1.5}` |
| `done` | Pipeline complete | `run_id` as string |
| `cancelled` | User cancelled | Message string |
| `error` | Fatal error | Error message string |

### 3.8 Observability

#### MLflow (`api/utils/tracking.py`)

- **Config:** `MLFLOW_TRACKING_URI` (default `""` — disabled)
- **Experiment:** `MLFLOW_EXPERIMENT_NAME` (default `"investment_research"`)
- **Lifecycle:** `init_tracking()` called during app startup; skipped if URI is empty
- **Logged entities:**

| Entity | Params | Metrics |
|---|---|---|
| LLM call | `model`, `agent`, `research_run_id`, `success` | `prompt_chars`, `response_chars`, `duration_sec` |
| Agent step | `agent`, `research_run_id`, `status`, `meta_*` | `duration_sec` |
| Research run | `research_run_id`, `question`, `llm_model`, `embedding_model`, `status` | Custom metrics |
| Embedding call | `model`, `success` | `text_chars`, `duration_sec` |

Each logged entity creates a nested run under the active MLflow experiment.

#### Langfuse (`api/utils/langfuse_tracking.py`)

- **Config:** `LANGFUSE_HOST`, `LANGFUSE_PUBLIC_KEY`, `LANGFUSE_SECRET_KEY` (all default `""` — disabled)
- **Lifecycle:** `init_langfuse()` during app startup
- **Global context:** `ContextVar` for current trace and span — allows nested tracing without passing objects
- **Logged entities:**

| Entity | Langfuse Object | Parent |
|---|---|---|
| Research run | `trace` | Root |
| Agent step | `span` | Trace |
| LLM call | `generation` | Current span or trace |
| Embedding call | `generation` | Current trace |

- **Flush:** `flush()` called at end of each workflow run to ensure events are sent

### 3.9 Frontend (`frontend/`)

#### Templates

**`index.html`** — Single-page application layout:
- Responsive two-column grid (single column below 640px)
- Collapsible sections with localStorage persistence
- Live health status dot in navbar (green/red, polls every 10s)
- Agent timeline: hidden div populated by SSE events during streaming
- Research history table with View links

**`report.html`** — Report viewer:
- Renders `{{ report|safe }}` (pre-converted from Markdown to HTML)
- Shows research question and run ID badge

#### JavaScript (`main.js` — 390 lines)

| Concern | Mechanism |
|---|---|
| Document list | `GET /documents` every 3s |
| Health check | `GET /health` every 10s |
| Upload | POST multipart/form-data, then poll `GET /documents/{id}` for up to 180s |
| Streaming research | `POST /research/stream` → `fetch()` with `ReadableStream` reader parsing SSE events |
| Async research | `POST /research/async` → returns `{research_id}`, polls history |
| Cancellation | `POST /research/{id}/cancel` + `AbortController.abort()` |
| Delete document | Confirmation dialog → `DELETE /documents/{id}` |

**SSE parsing:** The JS reads raw SSE stream events as `event: <type>\ndata: <json>\n\n` lines from the `ReadableStream` and dispatches to handler functions.

#### CSS (`style.css` — 720 lines)

CSS custom properties for theming: `--primary`, `--bg`, `--card-bg`, `--radius`, `--shadow`, etc.
Components: navbar, cards, buttons (3 variants), forms, tables, status badges (6 variants), agent timeline (4 states), progress bars, spinners, collapse sections, skeleton loading.

---

## 4. Configuration Reference

All settings in `config/settings.py` with `os.getenv()` fallbacks for Docker deployment.

| Variable | Default | Docker override | Purpose |
|---|---|---|---|
| `DATABASE_URL` | `postgresql://invest:invest@localhost:5432/invest_research` | `postgresql://invest:invest@postgres:5432/invest_research` | PostgreSQL connection |
| `QDRANT_URL` | `http://127.0.0.1:6333` | `http://qdrant:6333` | Qdrant HTTP endpoint |
| `QDRANT_COLLECTION` | `investment_docs` | — | Qdrant collection name |
| `OLLAMA_BASE_URL` | `http://127.0.0.1:11434` | `http://host.docker.internal:11434` | Ollama API endpoint |
| `LLM_MODEL` | `mistral:7b` | `gemma4:12b` | Primary generation model |
| `FALLBACK_LLM_MODEL` | `gemma4:12b` | — | Fallback LLM model |
| `LLM_TIMEOUT` | `3600` | `3600` | Max seconds per LLM call |
| `EMBEDDING_MODEL` | `nomic-embed-text` | — | Embedding model |
| `EMBEDDING_DIM` | `768` | — | Vector dimension |
| `MLFLOW_TRACKING_URI` | `""` (disabled) | — | MLflow server URI |
| `MLFLOW_EXPERIMENT_NAME` | `investment_research` | — | MLflow experiment |
| `LANGFUSE_HOST` | `""` (disabled) | — | Langfuse host URL |
| `LANGFUSE_PUBLIC_KEY` | `""` | — | Langfuse API public key |
| `LANGFUSE_SECRET_KEY` | `""` | — | Langfuse API secret key |
| `MCP_ENABLED` | `True` | `True` | Enable MCP integration |
| `MCP_HOST` | `127.0.0.1` | — | MCP bind address |
| `MCP_PORT` | `8100` | — | MCP port (internal) |

---

## 5. API Reference

### Health

```
GET /health
→ 200 {"app": "ok", "qdrant": "ok", "ollama": "ok (5 models)", "llm_model": "mistral:7b",
       "available_models": [...], "database": "ok"}
```

### Documents

```
POST /documents/upload
  Content-Type: multipart/form-data
  file: binary (PDF/DOCX/TXT)
  company: str (optional)
→ 200 {"message": "...", "document_id": 42, "status": "pending"}

GET /documents
→ 200 [{"id": 1, "filename": "...", "company": "...", "status": "ready",
        "chunk_count": 187, "processed_chunks": 187, "error": null, "uploaded_at": "..."}]

GET /documents/{id}
→ 200 same structure as above

DELETE /documents/{id}
→ 200 {"message": "Deleted", "filename": "..."}
  Cascades: removes file from disk, deletes Qdrant vectors via delete_by_filename(), deletes DB record
```

### Research

```
POST /research
  Form: question=str
→ 200 {"research_id": 5}

POST /research/async
  Form: question=str
→ 200 {"research_id": 5, "status": "running", "message": "Research started in background"}

POST /research/stream
  Form: question=str
→ 200 SSE stream with event types: config, status, agent_start, agent_done, agent_error, done, cancelled, error

GET /research/{id}
→ 200 {"id": 5, "question": "...", "status": "running"}

POST /research/{id}/cancel
→ 200 {"message": "Cancelled"}

GET /research/{id}/report
→ 200 {"report": "# Investment Research Report\n\n## Executive Summary\n\n..."}

GET /research/{id}/findings
→ 200 [{"id": 1, "topic": "Profitability", "content": "..."}]

GET /history
→ 200 [{"id": 5, "question": "...", "status": "completed", "created_at": "..."}]  (last 20)

GET /research/{id}/report.html
→ 200 HTML page with rendered report
```

### MCP

```
GET /mcp/tools
→ 200 [{"name": "get_stock_ticker", "description": "...", "inputSchema": {...}}, ...]

POST /mcp/call
  JSON: {"tool": "get_company_info", "args": {"company": "RBC"}}
→ 200 {"result": "..."}
```

---

## 6. Deployment

### Development (local)

```bash
# Start infrastructure
docker compose up -d postgres qdrant

# Run application
uvicorn api.main:app --reload --port 8000
```

### Docker (all containers)

```bash
docker compose up -d --build
```

Starts postgres, qdrant, and the app container. The app accesses Ollama on the host via `host.docker.internal`.

### Docker with Langfuse (optional)

```bash
docker compose --profile optional up -d langfuse
```

Langfuse becomes available at `http://localhost:3000`. Requires `LANGFUSE_HOST`, `LANGFUSE_PUBLIC_KEY`, `LANGFUSE_SECRET_KEY` to be configured.

### Docker on Linux

`host.docker.internal` may not resolve. Override `OLLAMA_BASE_URL`:
```bash
OLLAMA_BASE_URL=http://172.17.0.1:11434 docker compose up -d --build
```

---

## 7. Test Suite

24 tests across 8 test files:

| File | Tests | What it tests |
|---|---|---|
| `tests/agents/test_planner.py` | 2 | Init, run returns list (JSON parsing) |
| `tests/agents/test_researcher.py` | 1 | Init |
| `tests/agents/test_risk_analyst.py` | 2 | Init, run returns list |
| `tests/agents/test_writer.py` | 1 | Init |
| `tests/agents/test_reviewer.py` | 2 | Init, run returns dict |
| `tests/tools/test_calculator.py` | 5 | Growth rate, margin, ROE, ROA calculations |
| `tests/tools/test_document_loader.py` | 5 | File type support detection |
| `tests/workflows/test_research_workflow.py` | 1 | Init |
| `tests/test_evaluation_metrics.py` | 5 | Citation counting, completeness, report length |

**Run tests:**
```bash
DATABASE_URL=sqlite:///:memory: PYTHONPATH=$PWD python3 -m pytest tests/ -v
```

Agent tests monkeypatch `call_llm` to return predefined JSON without calling Ollama.

---

## 8. Data Flow Summary

```
1. User uploads PDF/DOCX/TXT
   └→ File saved to disk
   └→ DB record created (status=pending)
   └→ Background thread: extract → chunk → embed → Qdrant store
   └→ UI polls every 3s, shows "47 / 187" chunks

2. User submits research question
   └→ SSE stream opened (or async thread started)
   └→ Planner breaks question into tasks
   └→ For each task:
       ├→ Embed task → Qdrant search → evidence chunks
       ├→ MCP enrichment (company info, peers, ticker)
       └→ LLM summarizes findings
   └→ Risk Analyst reviews all findings
   └→ Writer composes Markdown report
   └→ Reviewer validates (up to 2 revision cycles)
   └→ Report stored in PostgreSQL
   └→ UI shows completed report with HTML rendering

3. Observability (opt-in):
   ├→ MLflow: runs, params, metrics per LLM call / agent / run
   └→ Langfuse: traces, spans, generations with full input/output
```

---

## 9. Project Structure

```
investment-research-agent/
├── api/
│   ├── agents/              # AI agents
│   │   ├── __init__.py      # Re-exports all agents
│   │   ├── base.py          # Abstract base class
│   │   ├── planner.py       # Research task planner
│   │   ├── researcher.py    # Evidence + MCP researcher
│   │   ├── risk_analyst.py  # Risk identification
│   │   ├── writer.py        # Report writer
│   │   └── reviewer.py      # Quality reviewer
│   ├── evaluation/          # Benchmark and metrics
│   ├── memory/              # PostgreSQL + Vector memory
│   │   ├── __init__.py
│   │   ├── postgres_memory.py   # ResearchRun, Finding, Report, Metric CRUD
│   │   ├── vector_memory.py     # Qdrant wrapper
│   │   └── reflections.py       # File-based JSON storage
│   ├── models/              # SQLAlchemy ORM models
│   │   ├── __init__.py
│   │   ├── company.py       # Document model
│   │   ├── research_run.py  # ResearchRun model
│   │   ├── finding.py       # Finding model
│   │   └── report.py        # Report + EvaluationMetric models
│   ├── tools/               # Tool implementations
│   │   ├── __init__.py
│   │   ├── calculator.py    # Financial calculators
│   │   ├── document_loader.py   # PDF/DOCX/TXT loader
│   │   ├── filing_search.py     # SEC filing search (stub)
│   │   ├── qdrant_search.py     # Qdrant CRUD operations
│   │   ├── mcp_server.py    # MCP stdio server (4 tools)
│   │   └── mcp_client.py    # MCP client (background event loop)
│   ├── utils/
│   │   ├── __init__.py
│   │   ├── llm.py           # Ollama client + fallback + tracking
│   │   ├── indexer.py       # Background document indexer
│   │   ├── markdown.py      # Markdown→HTML renderer
│   │   ├── tracking.py      # MLflow observability
│   │   └── langfuse_tracking.py  # Langfuse observability
│   ├── workflows/
│   │   ├── __init__.py
│   │   ├── research_workflow.py  # Agent pipeline orchestrator
│   │   └── review_workflow.py
│   ├── database.py          # DB engine, session, migrations
│   └── main.py              # FastAPI app with all endpoints
├── config/
│   └── settings.py          # All configuration
├── frontend/
│   ├── static/
│   │   ├── css/style.css    # 720 lines of custom CSS
│   │   ├── js/main.js       # 390 lines of JS (SSE, polling, UI)
│   │   └── images/favicon.ico
│   └── templates/
│       ├── index.html       # Main SPA
│       └── report.html      # Report viewer
├── data/                    # Uploaded documents
├── tests/                   # 24 tests
├── docker-compose.yml       # postgres + qdrant + langfuse(opt) + app
├── Dockerfile               # Python 3.12-slim
├── requirements.txt         # 14 dependencies
└── README.md
```

---

## 10. Dependencies

| Package | Version | Purpose |
|---|---|---|
| `fastapi` | 0.115.0 | Web framework |
| `uvicorn` | ≥0.30.6, <0.32.0 | ASGI server |
| `sqlalchemy` | 2.0.35 | ORM |
| `psycopg2-binary` | 2.9.9 | PostgreSQL driver |
| `httpx` | 0.27.2 | HTTP client for Ollama API |
| `langchain` | 0.3.0 | Document loaders, text splitter |
| `langchain-community` | 0.3.0 | PyPDFLoader, Docx2txtLoader |
| `pypdf` | 4.3.1 | PDF text extraction |
| `python-docx` | 1.1.2 | DOCX text extraction |
| `qdrant-client` | ≥1.11.0 | Qdrant HTTP client |
| `jinja2` | 3.1.4 | Template engine |
| `python-multipart` | 0.0.9 | File upload parsing |
| `pydantic` | 2.9.2 | Data validation |
| `mlflow` | ≥3.14.0 | ML experiment tracking (opt-in) |
| `langfuse` | ≥2.64.0 | LLM observability (opt-in) |
