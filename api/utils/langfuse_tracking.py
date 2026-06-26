import logging
import time
from contextvars import ContextVar
from typing import Any

from config.settings import LANGFUSE_HOST, LANGFUSE_PUBLIC_KEY, LANGFUSE_SECRET_KEY

logger = logging.getLogger(__name__)

_langfuse_available = False
_lf = None

_current_trace: ContextVar[Any | None] = ContextVar("langfuse_trace", default=None)
_current_span: ContextVar[Any | None] = ContextVar("langfuse_span", default=None)


def init_langfuse():
    global _langfuse_available, _lf
    if not LANGFUSE_HOST:
        logger.info("Langfuse tracking disabled (LANGFUSE_HOST not set)")
        return
    try:
        from langfuse import Langfuse

        _lf = Langfuse(
            host=LANGFUSE_HOST,
            public_key=LANGFUSE_PUBLIC_KEY,
            secret_key=LANGFUSE_SECRET_KEY,
        )
        _langfuse_available = True
        logger.info("Langfuse initialized: host=%s", LANGFUSE_HOST)
    except Exception as e:
        logger.warning("Failed to initialize Langfuse: %s", e)


def start_trace(name: str, **kwargs) -> Any | None:
    if not _langfuse_available:
        return None
    try:
        trace = _lf.trace(name=name, **kwargs)
        _current_trace.set(trace)
        return trace
    except Exception as e:
        logger.debug("Langfuse start_trace failed: %s", e)
        return None


def end_trace():
    trace = _current_trace.get()
    if trace:
        try:
            trace.end()
        except Exception:
            pass
        _current_trace.set(None)
    _current_span.set(None)


def start_span(name: str, **kwargs) -> Any | None:
    if not _langfuse_available:
        return None
    try:
        trace = _current_trace.get()
        if trace:
            span = trace.span(name=name, **kwargs)
        else:
            span = _lf.span(name=name, **kwargs)
        _current_span.set(span)
        return span
    except Exception as e:
        logger.debug("Langfuse start_span failed: %s", e)
        return None


def end_span():
    span = _current_span.get()
    if span:
        try:
            span.end()
        except Exception:
            pass
        _current_span.set(None)


def log_generation(
    name: str,
    model: str,
    input: str,
    output: str,
    duration: float,
    **kwargs,
):
    if not _langfuse_available:
        return
    try:
        parent = _current_span.get() or _current_trace.get()
        if parent:
            parent.generation(
                name=name,
                model=model,
                input=input,
                output=output,
                usage={"output": len(output), "input": len(input)},
                **kwargs,
            )
    except Exception as e:
        logger.debug("Langfuse log_generation failed: %s", e)


def log_embedding(model: str, input: str, duration: float, **kwargs):
    if not _langfuse_available:
        return
    try:
        trace = _current_trace.get()
        if trace:
            trace.generation(
                name="embedding",
                model=model,
                input=input,
                usage={"input": len(input)},
                **kwargs,
            )
    except Exception as e:
        logger.debug("Langfuse log_embedding failed: %s", e)


def flush():
    if _langfuse_available and _lf:
        try:
            _lf.flush()
        except Exception:
            pass
