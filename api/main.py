import logging
from pathlib import Path

from fastapi import FastAPI, UploadFile, File, Form, Depends, HTTPException
from fastapi.responses import HTMLResponse, StreamingResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from starlette.requests import Request
from sqlalchemy import text
from sqlalchemy.orm import Session

from api.database import get_db, init_db
from api.memory import PostgresMemory
from api.tools import DocumentLoader, QdrantSearch
from api.workflows import ResearchWorkflow, cancel_run
from api.utils.markdown import md_to_html
from api.utils.tracking import init_tracking
from api.models import Document
from api.utils.indexer import index_document
from api.utils.langfuse_tracking import init_langfuse
from config.settings import MCP_ENABLED

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(title="Investment Research Analyst Agent")

app.mount("/static", StaticFiles(directory="frontend/static"), name="static")
templates = Jinja2Templates(directory="frontend/templates")


@app.on_event("startup")
def on_startup():
    init_db()
    init_tracking()
    init_langfuse()
    if MCP_ENABLED:
        try:
            from api.tools.mcp_client import get_client
            get_client()
            logger.info("MCP client initialized")
        except Exception as e:
            logger.warning("MCP client initialization skipped: %s", e)


@app.get("/health")
def health():
    status = {"app": "ok"}

    try:
        from api.tools import QdrantSearch
        s = QdrantSearch()
        s.client.get_collections()
        status["qdrant"] = "ok"
    except Exception as e:
        status["qdrant"] = f"unavailable ({e})"

    try:
        import httpx
        from config.settings import OLLAMA_BASE_URL, LLM_MODEL
        r = httpx.get(f"{OLLAMA_BASE_URL}/api/tags", timeout=5)
        if r.status_code == 200:
            models = [m["name"] for m in r.json().get("models", [])]
            status["ollama"] = f"ok ({len(models)} models)"
            status["llm_model"] = LLM_MODEL
            status["available_models"] = models
        else:
            status["ollama"] = f"error ({r.status_code})"
    except Exception as e:
        status["ollama"] = f"unavailable ({e})"

    try:
        from api.database import SessionLocal
        db = SessionLocal()
        db.execute(text("SELECT 1"))
        db.close()
        status["database"] = "ok"
    except Exception as e:
        status["database"] = f"error ({e})"

    return status


@app.get("/", response_class=HTMLResponse)
def index(request: Request):
    return templates.TemplateResponse(request, "index.html", {"request": request})


@app.post("/documents/upload")
def upload_document(
    file: UploadFile = File(...),
    company: str = Form(""),
    db: Session = Depends(get_db),
):
    if not DocumentLoader.is_supported(file.filename):
        raise HTTPException(400, f"Unsupported file type: {file.filename}")

    upload_dir = Path("data") / "annual_reports"
    upload_dir.mkdir(parents=True, exist_ok=True)
    file_path = upload_dir / file.filename

    with open(file_path, "wb") as f:
        f.write(file.file.read())

    doc = Document(filename=file.filename, company=company, status="pending")
    db.add(doc)
    db.commit()
    db.refresh(doc)

    index_document(doc.id)

    return {
        "message": "Document uploaded and queued for indexing",
        "document_id": doc.id,
        "status": "pending",
    }


@app.get("/documents")
def list_documents(db: Session = Depends(get_db)):
    docs = db.query(Document).order_by(Document.uploaded_at.desc()).all()
    return [
        {
            "id": d.id,
            "filename": d.filename,
            "company": d.company,
            "status": d.status,
            "chunk_count": d.chunk_count,
            "processed_chunks": d.processed_chunks if d.status == "processing" else d.chunk_count,
            "error": d.error_message,
            "uploaded_at": str(d.uploaded_at),
        }
        for d in docs
    ]


@app.delete("/documents/{doc_id}")
def delete_document(doc_id: int, db: Session = Depends(get_db)):
    doc = db.query(Document).filter(Document.id == doc_id).first()
    if not doc:
        raise HTTPException(404, "Document not found")

    file_path = Path("data") / "annual_reports" / doc.filename
    if file_path.exists():
        file_path.unlink()

    try:
        search = QdrantSearch()
        search.delete_by_filename(doc.filename)
    except Exception as e:
        logger.warning("Qdrant delete skipped: %s", e)

    db.delete(doc)
    db.commit()

    return {"message": f"Document {doc_id} deleted", "filename": doc.filename}


@app.get("/documents/{doc_id}")
def get_document_status(doc_id: int, db: Session = Depends(get_db)):
    doc = db.query(Document).filter(Document.id == doc_id).first()
    if not doc:
        raise HTTPException(404, "Document not found")
    return {
        "id": doc.id,
        "filename": doc.filename,
        "company": doc.company,
        "status": doc.status,
        "chunk_count": doc.chunk_count,
        "processed_chunks": doc.processed_chunks if doc.status == "processing" else doc.chunk_count,
        "error": doc.error_message,
        "uploaded_at": str(doc.uploaded_at),
    }


@app.post("/research")
def create_research(question: str = Form(...), db: Session = Depends(get_db)):
    workflow = ResearchWorkflow(db)
    run_id = workflow.run(question)
    return {"research_id": run_id}


@app.post("/research/async")
def create_research_async(question: str = Form(...), db: Session = Depends(get_db)):
    workflow = ResearchWorkflow(db)
    run_id = workflow.run_async(question)
    return {"research_id": run_id, "status": "running", "message": "Research started in background. Poll /research/{id} for status."}


@app.post("/research/stream")
async def research_stream(question: str = Form(...), db: Session = Depends(get_db)):
    workflow = ResearchWorkflow(db)

    async def event_generator():
        for step, msg in workflow.run_stream(question):
            yield f"event: {step}\ndata: {msg}\n\n"
            if step == "done":
                yield f"event: done\ndata: {msg}\n\n"

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )


@app.get("/research/{run_id}")
def get_research_status(run_id: int, db: Session = Depends(get_db)):
    memory = PostgresMemory(db)
    run = memory.get_run(run_id)
    if not run:
        raise HTTPException(404, "Research run not found")
    return {"id": run.id, "status": run.status, "question": run.question}


@app.post("/research/{run_id}/cancel")
def cancel_research(run_id: int, db: Session = Depends(get_db)):
    memory = PostgresMemory(db)
    run = memory.get_run(run_id)
    if not run:
        raise HTTPException(404, "Research run not found")
    if run.status != "running":
        raise HTTPException(400, f"Cannot cancel run with status '{run.status}'")
    cancel_run(run_id)
    return {"message": f"Cancellation requested for run {run_id}"}


@app.get("/research/{run_id}/report")
def get_report(run_id: int, db: Session = Depends(get_db)):
    memory = PostgresMemory(db)
    report = memory.get_report(run_id)
    if not report:
        raise HTTPException(404, "Report not found")
    return {"report": report.report_text}


@app.get("/research/{run_id}/findings")
def get_findings(run_id: int, db: Session = Depends(get_db)):
    memory = PostgresMemory(db)
    findings = memory.get_findings(run_id)
    return [
        {"id": f.id, "topic": f.topic, "content": f.content}
        for f in findings
    ]


@app.get("/history")
def get_history(db: Session = Depends(get_db)):
    from api.models import ResearchRun
    runs = db.query(ResearchRun).order_by(ResearchRun.created_at.desc()).limit(20).all()
    return [
        {"id": r.id, "question": r.question, "status": r.status, "created_at": str(r.created_at)}
        for r in runs
    ]


@app.get("/research/{run_id}/report.html", response_class=HTMLResponse)
def report_html(request: Request, run_id: int, db: Session = Depends(get_db)):
    memory = PostgresMemory(db)
    report = memory.get_report(run_id)
    run = memory.get_run(run_id)
    return templates.TemplateResponse(request, "report.html", {
        "request": request,
        "report": md_to_html(report.report_text) if report else "",
        "run_id": run_id,
        "question": run.question if run else "",
    })
