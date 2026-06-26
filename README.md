# Investment Research Analyst Agent

An open-source, local-first AI-powered investment research system. Upload company documents (annual reports, quarterly filings, earnings transcripts) and ask natural-language research questions. A multi-agent workflow analyzes your documents and produces structured investment research reports — all running entirely on your workstation.

---

## Features

- **Local-first** — No cloud dependencies. Everything runs on your machine using Ollama-hosted models.
- **Multi-agent workflow** — Planner, Researcher, Risk Analyst, Writer, and Reviewer agents collaborate to produce reports.
- **Live agent timeline** — Real-time streaming shows which agent is running, LLM model, prompt size, and duration.
- **Background document indexing** — Large PDFs are processed asynchronously; chunk progress updates live in the UI.
- **Vector search** — Documents are chunked, embedded, and stored in Qdrant for semantic retrieval.
- **Cancellable research** — Cancel a running workflow at any point; starts a new one automatically when you re-submit.
- **Async research** — Start research in a background thread and check results later.
- **MLflow observability** — Optional MLflow tracking for every LLM call, agent step, and embedding (configurable).
- **Langfuse observability** — Optional Langfuse tracing for LLM calls, agent steps, embeddings, and research run traces. Self-hosted via Docker or cloud-hosted.
- **MCP server integration** — Built-in MCP (Model Context Protocol) server with financial tools (company info, stock ticker lookup, peer comparison, document search). Agents automatically query live market data alongside document evidence.
- **Health monitoring** — Live navbar indicator shows PostgreSQL, Qdrant, Ollama, and MCP status at a glance.
- **Structured reports** — Generates professional reports rendered as HTML with proper headings, lists, and typography.
- **Research history** — All reports and findings are stored in PostgreSQL for future retrieval.
- **Collapsible sections** — Uploaded Documents and Research History panels collapse to save space.

---

## Architecture

```
                    User
                      |
                      v
                 Frontend (HTML/CSS/JS)
                      |
                      v
                    FastAPI
                      |
                      v
              Agent Workflow Engine
                      |
       --------------------------------
       |              |               |
       v              v               v
    Planner       Researcher     Risk Analyst
                      |
                      v
                   Writer
                      |
                      v
                 Reviewer

       --------------------------------
              Memory Layer
           PostgreSQL + Qdrant

       --------------------------------
               Tool Layer
           Ollama (LLM + Embeddings)
         MCP Server (Financial Tools)
```

### Agents

| Agent | Responsibility |
|---|---|
| **Planner** | Breaks down a research question into specific tasks (e.g., "Analyze profitability", "Analyze revenue growth") |
| **Researcher** | For each task, searches the vector database for relevant document chunks, retrieves evidence, enriches with live market data via MCP tools (company info, peers, ticker), and summarizes findings |
| **Risk Analyst** | Reviews all findings and identifies regulatory, market, interest-rate, and credit risks |
| **Writer** | Composes a complete investment research report in Markdown |
| **Reviewer** | Validates the report for completeness, evidence quality, and logical consistency. Up to 2 revision cycles. |

---

## Technology Stack

| Component | Technology |
|---|---|
| Backend | Python 3.12, FastAPI |
| Database | PostgreSQL 16 |
| Vector Database | Qdrant |
| LLM | Ollama (mistral:7b default, gemma4:12b fallback) |
| Embeddings | Ollama (nomic-embed-text recommended) |
| MCP | Model Context Protocol (Python `mcp` SDK), stdio transport |
| Observability | MLflow (opt-in), Langfuse (opt-in, self-hosted or cloud) |
| Frontend | HTML, CSS, JavaScript |
| Document Processing | PyPDF, python-docx |

---

## Getting Started

### Prerequisites

- Python 3.12+
- [Ollama](https://ollama.ai) installed and running
- [Docker](https://docker.com) and Docker Compose (for PostgreSQL + Qdrant, optional Langfuse)
- An LLM model pulled via Ollama

### 1. Clone and set up

```bash
git clone <your-repo-url>
cd investment-research-agent
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

### 2. Pull models

You need **two** models — one for generation (LLM) and one for embeddings. Chat models like `gemma4` cannot generate embeddings; a dedicated embedding model is required.

```bash
# Generation model (for agents)
ollama pull mistral:7b

# Embedding model (for document vector search)
ollama pull nomic-embed-text
```

Other generation models: `gemma4:12b`, `llama3.1:8b`, `mistral:7b`  
Other embedding models: `all-minilm:latest`, `nomic-embed-text`, `mxbai-embed-large`

The system automatically falls back through multiple embedding/LLM models if the primary fails.

### 3. Start infrastructure (PostgreSQL + Qdrant)

```bash
docker compose up -d postgres qdrant
```

### 4. Configure (optional)

Edit `config/settings.py` to change model, timeouts, or database URLs:

```python
# config/settings.py
LLM_MODEL = "mistral:7b"            # Primary generation model
FALLBACK_LLM_MODEL = "gemma4:12b"   # Fallback if primary fails/times out
LLM_TIMEOUT = 3600                  # Max seconds per LLM call
EMBEDDING_MODEL = "nomic-embed-text"
DATABASE_URL = "postgresql://invest:invest@localhost:5432/invest_research"
QDRANT_URL = "http://127.0.0.1:6333"
```

### 5. Run the application

```bash
uvicorn api.main:app --reload --port 8000
```

Open [http://localhost:8000](http://localhost:8000) in your browser.

### 6. Run everything with Docker

Prefer to run the entire stack in containers? A single command starts PostgreSQL, Qdrant, and the app server:

```bash
docker compose up -d --build
```

This builds the app image from the `Dockerfile` and starts all three services. The app connects to PostgreSQL and Qdrant via Docker's internal network.

**Environment overrides:**

The `docker-compose.yml` sets Docker-friendly defaults for the app container:

| Variable | Docker value | Reason |
|---|---|---|
| `DATABASE_URL` | `postgresql://invest:invest@postgres:5432/invest_research` | Points to the `postgres` container |
| `QDRANT_URL` | `http://qdrant:6333` | Points to the `qdrant` container |
| `OLLAMA_BASE_URL` | `http://host.docker.internal:11434` | Accesses Ollama running on the host |
| `LLM_MODEL` | `gemma4:12b` | Faster within container resources |

These env vars override the defaults in `config/settings.py`. Edit `docker-compose.yml` or pass inline overrides:

```bash
LLM_MODEL=mistral:7b docker compose up -d --build
```

**Start Langfuse (optional):**

```bash
docker compose --profile optional up -d langfuse
```

**With Ollama on Linux:**

`host.docker.internal` may not resolve on Linux. If the app can't reach Ollama, override `OLLAMA_BASE_URL` to use the host network or your machine's LAN IP:

```bash
# Option A: use host networking for the app container
OLLAMA_BASE_URL=http://172.17.0.1:11434 docker compose up -d --build

# Option B: edit docker-compose.yml, add network_mode: "host" under the app service
```

**View logs:**

```bash
docker compose logs -f app
```

### Run without Docker

If you don't have Docker, use SQLite (vector search requires Qdrant, but document metadata works):

```bash
# Edit config/settings.py to use:
# DATABASE_URL = "sqlite:///./data/research.db"

uvicorn api.main:app --reload --port 8000
```

---

## Usage

### Upload a Document

1. Open the web UI at `http://localhost:8000`
2. Under **Upload Documents**, select a PDF, DOCX, or TXT file
3. Optionally enter a company name
4. Click **Upload & Index**

**How it works:**
- The file is saved to `data/annual_reports/`
- A database record is created with status `pending`
- A background thread processes the document:
  1. Extracts text from the file
  2. Splits text into chunks
  3. Generates embeddings via Ollama
  4. Stores vectors in Qdrant
  5. Updates status to `ready`
- The **Chunks** column shows live progress (e.g. `47 / 187`) during indexing
- If indexing fails, a ⚠ tooltip shows the error message
- Multiple documents can be uploaded in parallel

### Ask a Research Question

1. In the **Research Question** section, type your question
2. Examples:
   - *"Compare RBC and TD Bank as long-term investments"*
   - *"Analyze the risks facing TD Bank"*
   - *"Summarize RBC's recent earnings performance"*
3. Click **Start Research** for a live streaming timeline, or **Start Async →** to run in the background

**During streaming research:**
- A live **agent timeline** appears showing each agent step
- Each step shows: status (spinner / ✓ / ✗), model, duration, and LLM response size
- Click **Cancel** at any time to stop the workflow
- Submit a new question while one is running — the old one is cancelled automatically

**Async research:**
- Returns immediately with a research ID
- Poll `GET /research/{id}` for status, or check the Research History table
- View the completed report at `/research/{id}/report.html`
- Useful for long-running research — close the browser and come back later

### View Reports

- Completed reports appear in the **Research History** table
- Click **View** to see the full report with proper HTML formatting
- Reports include: Executive Summary, Company Overview, Financial Analysis, Strategic Analysis, Risk Analysis, Investment Thesis, and Conclusion

### Health Monitoring

The navbar shows a live status indicator:
- **Green dot** — All systems operational
- **Red dot** — Specific service offline (Qdrant, Ollama, or database)

### Langfuse Observability

Langfuse provides a web dashboard for tracing, debugging, and analyzing LLM calls, agent steps, and research runs.

**Enable Langfuse (self-hosted):**

```bash
# Start Langfuse alongside PostgreSQL
docker compose --profile optional up -d langfuse
```

Langfuse will be available at `http://localhost:3000`. On first visit, create an account, then generate API keys in **Settings → API Keys**.

**Configure in `config/settings.py`:**

```python
LANGFUSE_HOST = "http://localhost:3000"
LANGFUSE_PUBLIC_KEY = "pk-..."
LANGFUSE_SECRET_KEY = "sk-..."
```

**What gets traced:**
- **Research runs** — Each research workflow (`run`, `run_async`, `run_stream`) creates a top-level trace
- **Agent steps** — Each agent (Planner, Researcher, RiskAnalyst, Writer, Reviewer) creates a span within the trace
- **LLM calls** — Every `call_llm` invocation is logged as a generation with model, prompt, response, and duration
- **Embedding calls** — Each `get_embedding` call is logged as a generation with model and input length

**Cloud option:** Set `LANGFUSE_HOST` to `https://cloud.langfuse.com` and use your cloud API keys instead.

---

## API Endpoints

| Method | Endpoint | Description |
|---|---|---|
| `GET` | `/` | Web UI |
| `GET` | `/health` | Service health check (app, qdrant, ollama, database) |
| `POST` | `/documents/upload` | Upload a document (returns immediately, indexes in background) |
| `GET` | `/documents` | List all documents with status and chunk progress |
| `GET` | `/documents/{id}` | Get document status and details |
| `DELETE` | `/documents/{id}` | Delete document, file, and Qdrant vectors |
| `POST` | `/research` | Start a research workflow (blocking, synchronous) |
| `POST` | `/research/async` | Start research in a background thread (returns immediately) |
| `POST` | `/research/stream` | Start a research workflow with SSE streaming + live agent timeline |
| `GET` | `/research/{id}` | Get research run status |
| `POST` | `/research/{id}/cancel` | Cancel a running research workflow |
| `GET` | `/research/{id}/report` | Get the generated report (JSON) |
| `GET` | `/research/{id}/report.html` | View the report as formatted HTML |
| `GET` | `/research/{id}/findings` | Get intermediate findings |
| `GET` | `/history` | List recent research runs |
| `GET` | `/mcp/tools` | List available MCP tools |
| `POST` | `/mcp/call` | Call an MCP tool (`{"tool": "...", "args": {...}}`) |

### MCP Server

The system includes a built-in **MCP (Model Context Protocol)** server that provides live financial data tools to the research agents:

| Tool | Description |
|---|---|
| `get_stock_ticker` | Look up a stock ticker symbol for a company name |
| `get_company_info` | Get company profile, sector, industry, market cap |
| `get_peers` | Find peer companies in the same sector/industry |
| `search_documents` | Semantic search across uploaded documents (Qdrant-backed) |

**How it works:**
- On startup, the app launches an MCP server as a subprocess via stdio transport
- The MCP client (`api/tools/mcp_client.py`) connects automatically in a background thread
- The **Researcher agent** calls MCP tools to enrich its analysis with live market data alongside document evidence
- Tools are available at `/mcp/tools` and `/mcp/call` for external use or debugging
- Controlled via `MCP_ENABLED = True` in `config/settings.py`

### Document Upload API Detail

```json
POST /documents/upload
Content-Type: multipart/form-data

file: (binary PDF/DOCX/TXT)
company: "RBC" (optional)

Response 200:
{
  "message": "Document uploaded and queued for indexing",
  "document_id": 42,
  "status": "pending"
}
```

Poll for completion:

```json
GET /documents/42

Response:
{
  "id": 42,
  "filename": "RBC_2024_Annual_Report.pdf",
  "company": "RBC",
  "status": "ready",
  "chunk_count": 187,
  "processed_chunks": 187,
  "error": null,
  "uploaded_at": "2026-06-25T12:00:00"
}
```

---

## Background Indexing

Large annual reports (100+ pages) can take 30-60 seconds to process. The system handles this in the background:

1. **Upload** — File is saved to disk and a database record is created. The API responds immediately.
2. **Threaded worker** — A daemon thread extracts text, chunks, embeds, and indexes into Qdrant.
3. **Status tracking** — Document status transitions: `pending` → `processing` → `ready` (or `failed`).
4. **Live progress** — The `processed_chunks` field updates as each chunk is indexed; the UI polls every 3 seconds.
5. **Error reporting** — Failed chunks and Qdrant errors are captured in the `error` field and shown in the UI.
6. **Parallel uploads** — Each document gets its own thread.

---

## Project Structure

```
investment-research-agent/
├── api/
│   ├── agents/              # AI agent implementations
│   │   ├── planner.py
│   │   ├── researcher.py
│   │   ├── risk_analyst.py
│   │   ├── writer.py
│   │   └── reviewer.py
│   ├── evaluation/          # Quality metrics and benchmarking
│   ├── memory/              # PostgreSQL and vector memory layers
│   ├── models/              # SQLAlchemy database models
│   ├── tools/               # Document loader, Qdrant search, calculator, MCP
│   │   ├── mcp_server.py    # MCP server with financial tools (company info, ticker, peers, search)
│   │   └── mcp_client.py    # MCP client wrapper (persistent stdio, auto-connect)
│   ├── utils/
│   │   ├── llm.py           # Ollama LLM client with fallback + MLflow tracking
│   │   ├── indexer.py       # Background document indexer
│   │   ├── markdown.py      # Markdown-to-HTML converter
│   │   ├── tracking.py      # MLflow observability (LLM calls, agents, runs)
│   │   └── langfuse_tracking.py  # Langfuse tracing (traces, spans, generations)
│   ├── workflows/
│   │   ├── research_workflow.py  # Multi-agent orchestration with streaming
│   │   └── review_workflow.py
│   ├── database.py          # Database engine, session, migrations
│   └── main.py              # FastAPI application and endpoints
├── config/
│   └── settings.py          # Plain Python configuration (no env vars)
├── frontend/
│   ├── static/
│   │   ├── css/
│   │   ├── js/
│   │   └── images/
│   └── templates/
│       ├── index.html
│       └── report.html
├── data/                    # Uploaded documents
├── tests/
├── docker-compose.yml
├── Dockerfile
├── requirements.txt
└── README.md
```

---

## Configuration

All configuration is in `config/settings.py`:

| Variable | Default | Description |
|---|---|---|
| `DATABASE_URL` | `postgresql://invest:invest@localhost:5432/invest_research` | PostgreSQL connection string |
| `QDRANT_URL` | `http://127.0.0.1:6333` | Qdrant vector database URL |
| `QDRANT_COLLECTION` | `investment_docs` | Qdrant collection name |
| `OLLAMA_BASE_URL` | `http://localhost:11434` | Ollama API base URL |
| `LLM_MODEL` | `mistral:7b` | Primary model for agent LLM calls |
| `FALLBACK_LLM_MODEL` | `gemma4:12b` | Fallback if primary fails/times out |
| `LLM_TIMEOUT` | `3600` | Max seconds per LLM call |
| `EMBEDDING_MODEL` | `nomic-embed-text` | Model for embeddings (must support Ollama's embedding API) |
| `EMBEDDING_DIM` | `768` | Vector dimension (must match embedding model output) |
| `MLFLOW_TRACKING_URI` | `""` (disabled) | MLflow tracking server URI (e.g. `http://localhost:5000`) |
| `MLFLOW_EXPERIMENT_NAME` | `investment_research` | MLflow experiment name |
| `MCP_ENABLED` | `True` | Enable/disable MCP server |
| `MCP_HOST` | `127.0.0.1` | MCP server bind address (internal) |
| `MCP_PORT` | `8100` | MCP server port (internal) |
| `LANGFUSE_HOST` | `""` (disabled) | Langfuse host URL (e.g. `http://localhost:3000`) |
| `LANGFUSE_PUBLIC_KEY` | `""` | Langfuse public API key (from Settings → API Keys) |
| `LANGFUSE_SECRET_KEY` | `""` | Langfuse secret API key |

Edit the file directly — there are no `.env` files or environment variables.

---

## Running Tests

```bash
# Install test dependencies
pip install pytest

# Run all tests (24 passing)
DATABASE_URL=sqlite:///:memory: PYTHONPATH=$PWD python3 -m pytest tests/ -v
```

---

## Development Roadmap

- [x] Document upload and indexing
- [x] Vector search with Qdrant
- [x] Multi-agent research workflow
- [x] Report generation and review
- [x] Background document processing
- [x] Streaming agent execution in UI
- [x] Live agent timeline with LLM metrics
- [x] Cancellable research workflows
- [x] Collapsible UI sections
- [x] Health monitoring dashboard
- [x] Async research workflows
- [x] MLflow experiment tracking
- [x] MCP server integration
- [x] Langfuse observability

---

## License
MIT

