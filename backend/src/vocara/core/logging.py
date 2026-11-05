"""Structured logging configuration for Vocara."""

import http
import logging
import sys
from contextvars import ContextVar
from typing import Any, cast

import structlog

# Context variables to hold correlation and tenant metadata per async context
request_id_ctx: ContextVar[str | None] = ContextVar("request_id_ctx", default=None)
user_id_ctx: ContextVar[str | None] = ContextVar("user_id_ctx", default=None)
tenant_id_ctx: ContextVar[str | None] = ContextVar("tenant_id_ctx", default=None)


def add_request_context(
    _: Any, __: str, event_dict: structlog.types.EventDict
) -> structlog.types.EventDict:
    """Processor to inject correlation/request ID, user ID, and tenant ID into log records."""
    req_id = request_id_ctx.get()
    if req_id:
        event_dict["requestId"] = req_id
    user_id = user_id_ctx.get()
    if user_id:
        event_dict["userId"] = user_id
    tenant_id = tenant_id_ctx.get()
    if tenant_id:
        event_dict["tenantId"] = tenant_id
    return event_dict


# Backwards compatibility alias
add_request_id = add_request_context


class ColorizedConsoleRenderer:
    """Concise, high-readability ANSI-colorized console renderer for developers."""

    RESET = "\033[0m"
    BOLD = "\033[1m"
    DIM = "\033[2m"
    GREEN = "\033[1;32m"
    YELLOW = "\033[1;33m"
    RED = "\033[1;31m"
    CYAN = "\033[36m"
    MAGENTA = "\033[35m"

    LEVEL_BADGES = {
        "debug": f"{CYAN}[DEBUG]{RESET}",
        "info": f"{GREEN}[INFO ]{RESET}",
        "warning": f"{YELLOW}[WARN ]{RESET}",
        "warn": f"{YELLOW}[WARN ]{RESET}",
        "error": f"{RED}[ERROR]{RESET}",
        "critical": f"\033[1;41m[CRIT ]{RESET}",
    }

    def __call__(self, _: Any, __: str, event_dict: structlog.types.EventDict) -> str:
        timestamp = str(event_dict.pop("timestamp", ""))
        level = str(event_dict.pop("level", "info")).lower()
        event = str(event_dict.pop("event", ""))
        event_dict.pop("logger", None)

        # Extract clean HH:MM:SS time
        if "T" in timestamp:
            time_str = timestamp.split("T")[1].split(".")[0]
        elif len(timestamp) >= 8:
            time_str = timestamp[:8]
        else:
            time_str = ""

        ts_badge = f"{self.DIM}[{time_str}]{self.RESET} " if time_str else ""

        # 1. Concise HTTP Request Logs
        if event in ("http_request_completed", "http_request_client_error", "http_request_failed"):
            method = str(event_dict.get("method", "GET"))
            path = str(event_dict.get("path", "/"))
            status = event_dict.get("status", 200)
            duration_ms = event_dict.get("durationMs", 0)
            error = event_dict.get("error")

            try:
                st_code = int(status)
                phrase = http.HTTPStatus(st_code).phrase
                if st_code < 300:
                    status_str = f"{self.GREEN}{st_code} {phrase}{self.RESET}"
                elif st_code < 400:
                    status_str = f"{self.CYAN}{st_code} {phrase}{self.RESET}"
                elif st_code < 500:
                    status_str = f"{self.YELLOW}{st_code} {phrase}{self.RESET}"
                else:
                    status_str = f"{self.RED}{st_code} {phrase}{self.RESET}"
            except Exception:
                status_str = str(status)

            dur_str = (
                f" {self.MAGENTA}{round(float(duration_ms))}ms{self.RESET}"
                if duration_ms is not None
                else ""
            )
            err_str = f" - {self.YELLOW}{error}{self.RESET}" if error else ""

            return f"{ts_badge}{self.BOLD}{method:<5}{self.RESET} {self.CYAN}{path}{self.RESET} {status_str}{dur_str}{err_str}"

        # 2. Server Lifecycle Events
        if event == "application_startup":
            env = event_dict.get("environment", "development")
            host = event_dict.get("host", "0.0.0.0")
            port = event_dict.get("port", 8002)
            return f"{ts_badge}{self.GREEN}Vocara Voice API starting{self.RESET} in {env} mode (http://{host}:{port})"

        if event == "application_ready":
            host = event_dict.get("host", "0.0.0.0")
            port = event_dict.get("port", 8002)
            docs = event_dict.get("docsUrl", "")
            docs_info = f" {self.DIM}(Docs: {docs}){self.RESET}" if docs else ""
            return f"{ts_badge}{self.GREEN}Vocara Voice API ready{self.RESET} on http://{host}:{port}{docs_info}"

        if event == "application_shutdown":
            return f"{ts_badge}{self.YELLOW}Vocara Voice API shut down{self.RESET}"

        # 3. General Events (Strip verbose tracing fields from console display)
        badge = self.LEVEL_BADGES.get(level, f"[{level.upper():<5}]")
        clean_kvs = [
            f"{self.CYAN}{k}{self.RESET}={v}"
            for k, v in event_dict.items()
            if k not in ("requestId", "tenantId", "userId", "ip", "userAgent", "url")
        ]
        kvs_str = f" {' '.join(clean_kvs)}" if clean_kvs else ""
        return f"{ts_badge}{badge} {event}{kvs_str}"


def setup_logging(log_level: str = "INFO", log_format: str = "console") -> None:
    """Configure structured logging system."""
    level = getattr(logging, log_level.upper(), logging.INFO)

    shared_processors: list[structlog.types.Processor] = [
        structlog.contextvars.merge_contextvars,
        add_request_context,
        structlog.stdlib.add_logger_name,
        structlog.stdlib.add_log_level,
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.processors.StackInfoRenderer(),
        structlog.processors.format_exc_info,
    ]

    if log_format == "json":
        renderer: structlog.types.Processor = structlog.processors.JSONRenderer()
    else:
        renderer = ColorizedConsoleRenderer()

    structlog.configure(
        processors=shared_processors
        + [
            structlog.stdlib.ProcessorFormatter.wrap_for_formatter,
        ],
        logger_factory=structlog.stdlib.LoggerFactory(),
        wrapper_class=structlog.stdlib.BoundLogger,
        cache_logger_on_first_use=True,
    )

    formatter = structlog.stdlib.ProcessorFormatter(
        foreign_pre_chain=shared_processors,
        processors=[
            structlog.stdlib.ProcessorFormatter.remove_processors_meta,
            renderer,
        ],
    )

    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(formatter)

    root_logger = logging.getLogger()
    root_logger.handlers.clear()
    root_logger.addHandler(handler)
    root_logger.setLevel(level)

    # Route uvicorn and fastapi system loggers into structlog formatter
    for logger_name in ("uvicorn", "uvicorn.error", "fastapi"):
        uv_logger = logging.getLogger(logger_name)
        uv_logger.handlers.clear()
        uv_logger.propagate = True

    # Suppress verbose third-party HTTP wire logs to keep terminal structured and clean
    logging.getLogger("uvicorn.access").handlers.clear()
    logging.getLogger("uvicorn.access").propagate = False
    for noisy_logger in (
        "azure",
        "azure.core",
        "azure.core.pipeline.policies",
        "azure.core.pipeline.policies.http_logging_policy",
        "azure.storage",
        "azure.storage.blob",
        "httpx",
        "httpcore",
    ):
        logging.getLogger(noisy_logger).setLevel(logging.WARNING)


def get_logger(name: str = "vocara") -> structlog.stdlib.BoundLogger:
    """Return a configured structured logger."""
    return cast(structlog.stdlib.BoundLogger, structlog.get_logger(name))
