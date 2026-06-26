import logging
import time
from typing import Any

from config.settings import MLFLOW_TRACKING_URI, MLFLOW_EXPERIMENT_NAME, LLM_MODEL, EMBEDDING_MODEL

logger = logging.getLogger(__name__)

_mlflow_available = False
_client = None


def init_tracking():
    global _mlflow_available, _client
    if not MLFLOW_TRACKING_URI:
        logger.info("MLflow tracking disabled (MLFLOW_TRACKING_URI not set)")
        return
    try:
        import mlflow

        mlflow.set_tracking_uri(MLFLOW_TRACKING_URI)
        mlflow.set_experiment(MLFLOW_EXPERIMENT_NAME)
        _client = mlflow.MlflowClient()
        _mlflow_available = True
        logger.info("MLflow tracking initialized: uri=%s experiment=%s", MLFLOW_TRACKING_URI, MLFLOW_EXPERIMENT_NAME)
    except Exception as e:
        logger.warning("Failed to initialize MLflow: %s", e)


def _ensure_run(run_name: str | None = None) -> Any | None:
    if not _mlflow_available:
        return None
    try:
        import mlflow

        return mlflow.start_run(run_name=run_name, nested=True)
    except Exception as e:
        logger.debug("MLflow start_run failed: %s", e)
        return None


def log_llm_call(
    model: str,
    prompt_len: int,
    response_len: int,
    duration: float,
    run_id: int | None = None,
    agent: str | None = None,
    success: bool = True,
):
    if not _mlflow_available:
        return
    try:
        import mlflow

        run = _ensure_run(f"llm_{agent or 'unknown'}_{int(time.time())}")
        if not run:
            return
        mlflow.log_params({
            "model": model,
            "agent": agent or "unknown",
            "research_run_id": str(run_id) if run_id else "none",
        })
        mlflow.log_metrics({
            "prompt_chars": prompt_len,
            "response_chars": response_len,
            "duration_sec": round(duration, 2),
        })
        mlflow.log_param("success", str(success))
        mlflow.end_run()
    except Exception as e:
        logger.debug("MLflow log_llm_call failed: %s", e)


def log_agent_step(
    agent: str,
    duration: float,
    run_id: int,
    status: str = "completed",
    metadata: dict | None = None,
):
    if not _mlflow_available:
        return
    try:
        import mlflow

        run = _ensure_run(f"agent_{agent}_{run_id}")
        if not run:
            return
        mlflow.log_params({
            "agent": agent,
            "research_run_id": str(run_id),
            "status": status,
        })
        mlflow.log_metric("duration_sec", round(duration, 2))
        if metadata:
            for k, v in metadata.items():
                mlflow.log_param(f"meta_{k}", str(v)[:500])
        mlflow.end_run()
    except Exception as e:
        logger.debug("MLflow log_agent_step failed: %s", e)


def log_research_run(
    run_id: int,
    question: str,
    status: str,
    metrics: dict[str, Any] | None = None,
):
    if not _mlflow_available:
        return
    try:
        import mlflow

        run = _ensure_run(f"research_{run_id}")
        if not run:
            return
        mlflow.log_params({
            "research_run_id": str(run_id),
            "question": question[:500],
            "llm_model": LLM_MODEL,
            "embedding_model": EMBEDDING_MODEL,
            "status": status,
        })
        if metrics:
            for k, v in metrics.items():
                mlflow.log_metric(k, v)
        mlflow.end_run()
    except Exception as e:
        logger.debug("MLflow log_research_run failed: %s", e)


def log_embedding_call(model: str, text_len: int, duration: float, success: bool = True):
    if not _mlflow_available:
        return
    try:
        import mlflow

        run = _ensure_run(f"embedding_{int(time.time())}")
        if not run:
            return
        mlflow.log_params({"model": model, "success": str(success)})
        mlflow.log_metrics({"text_chars": text_len, "duration_sec": round(duration, 2)})
        mlflow.end_run()
    except Exception as e:
        logger.debug("MLflow log_embedding_call failed: %s", e)
