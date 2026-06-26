import logging
import time
from typing import Any, Callable

import httpx

from config.settings import OLLAMA_BASE_URL, LLM_MODEL, FALLBACK_LLM_MODEL, LLM_TIMEOUT, EMBEDDING_MODEL
from api.utils.tracking import log_llm_call, log_embedding_call, init_tracking
from api.utils.langfuse_tracking import log_generation as lf_log_generation, log_embedding as lf_log_embedding

logger = logging.getLogger(__name__)

# Initialize MLflow tracking on import
init_tracking()

# Track the current research run ID for MLflow context
_current_run_id: int | None = None


def set_run_id(run_id: int | None):
    global _current_run_id
    _current_run_id = run_id


def call_llm(
    prompt: str,
    system: str | None = None,
    model: str | None = None,
    on_start: Callable[[str, int], None] | None = None,
    on_finish: Callable[[str, int, float], None] | None = None,
) -> str:
    primary = model or LLM_MODEL
    fallback = FALLBACK_LLM_MODEL
    result = "Error: Unable to get response from LLM"
    for attempt, m in [(primary, primary), ("fallback", fallback)]:
        if attempt == "fallback" and m == primary:
            break
        url = f"{OLLAMA_BASE_URL}/api/generate"
        payload: dict[str, Any] = {
            "model": m,
            "prompt": prompt,
            "stream": False,
            "options": {"temperature": 0.3, "num_ctx": 8192},
        }
        if system:
            payload["system"] = system

        prompt_len = len(prompt)
        logger.info("LLM call: model=%s prompt_len=%d", m, prompt_len)
        if on_start:
            on_start(m, prompt_len)
        t0 = time.time()
        try:
            resp = httpx.post(url, json=payload, timeout=LLM_TIMEOUT)
            resp.raise_for_status()
            data = resp.json()
            output = data.get("response", "")
            dur = data.get("total_duration", 0) / 1e9
            actual_dur = dur if dur > 0 else time.time() - t0
            logger.info("LLM response: model=%s len=%d duration=%.1fs", m, len(output), actual_dur)
            if on_finish:
                on_finish(m, len(output), actual_dur)
            log_llm_call(
                model=m, prompt_len=prompt_len, response_len=len(output),
                duration=actual_dur, run_id=_current_run_id, success=True,
            )
            lf_log_generation(
                name="call_llm", model=m, input=prompt, output=output, duration=actual_dur,
            )
            result = output.strip()
            break
        except Exception as e:
            elapsed = time.time() - t0
            logger.error("LLM call failed with %s: %s", m, e)
            if on_finish:
                on_finish(m, 0, elapsed)
            log_llm_call(
                model=m, prompt_len=prompt_len, response_len=0,
                duration=elapsed, run_id=_current_run_id, success=False,
            )
            lf_log_generation(
                name="call_llm", model=m, input=prompt, output="", duration=elapsed,
                metadata={"error": str(e)},
            )
            if attempt == "fallback":
                result = f"Error: Unable to get response from LLM - {e}"

    return result


FALLBACK_EMBEDDING_MODELS = [
    EMBEDDING_MODEL,
    "nomic-embed-text",
    "all-minilm:latest",
    "mxbai-embed-large",
]


def get_embedding(text: str) -> list[float]:
    last_error = None
    for model in FALLBACK_EMBEDDING_MODELS:
        t0 = time.time()
        try:
            result = _try_embed(model, text)
            log_embedding_call(model=model, text_len=len(text), duration=time.time() - t0, success=True)
            lf_log_embedding(model=model, input=text, duration=time.time() - t0)
            return result
        except Exception as e:
            last_error = e
            log_embedding_call(model=model, text_len=len(text), duration=time.time() - t0, success=False)
            lf_log_embedding(model=model, input=text, duration=time.time() - t0, metadata={"error": str(e)})
            logger.warning("Embedding failed with model %s: %s", model, e)

    logger.error("All embedding models failed: %s", last_error)
    return [0.0] * 768


def _try_embed(model: str, text: str) -> list[float]:
    try:
        return _post_embed_v2(model, text)
    except Exception:
        return _post_embed_v1(model, text)


def _post_embed_v2(model: str, text: str) -> list[float]:
    url = f"{OLLAMA_BASE_URL}/api/embed"
    payload = {"model": model, "input": text}
    resp = httpx.post(url, json=payload, timeout=30)
    resp.raise_for_status()
    data = resp.json()
    embeddings = data.get("embeddings", [])
    if embeddings:
        return embeddings[0]
    raise ValueError(f"No embeddings in /api/embed response for {model}")


def _post_embed_v1(model: str, text: str) -> list[float]:
    url = f"{OLLAMA_BASE_URL}/api/embeddings"
    payload = {"model": model, "prompt": text}
    resp = httpx.post(url, json=payload, timeout=30)
    resp.raise_for_status()
    data = resp.json()
    embedding = data.get("embedding")
    if embedding:
        return embedding
    raise ValueError(f"No embedding in /api/embeddings response for {model}")
