"""
Logging configuration with structured format and OpenTelemetry integration.
"""

import logging
import logging.handlers
import sys
from datetime import datetime
from pathlib import Path

try:
    from opentelemetry import trace as otel_trace
    OTEL_AVAILABLE = True
except ImportError:
    OTEL_AVAILABLE = False


class StructuredFormatter(logging.Formatter):
    """Custom formatter that outputs structured log messages with trace context."""

    def format(self, record: logging.LogRecord) -> str:
        timestamp = datetime.utcnow().isoformat() + "Z"
        
        # Get OpenTelemetry trace context if available
        trace_id = "no-trace"
        if OTEL_AVAILABLE:
            try:
                span = otel_trace.get_current_span()
                span_context = span.get_span_context()
                if span_context:
                    trace_id = f"{span_context.trace_id:032x}"[:16]
            except Exception:
                pass

        log_message = (
            f"{timestamp} | "
            f"{trace_id} | "
            f"{record.levelname:<8} | "
            f"{record.name}:{record.lineno} | "
            f"{record.getMessage()}"
        )

        if record.exc_info:
            log_message += f"\n{self.formatException(record.exc_info)}"

        return log_message


def setup_logging(log_level: str = "INFO", log_file_path: str = "logs/dsh_etl_search_ai.log") -> None:
    """Configure application logging with both console and file output.
    
    Args:
        log_level: Logging level (INFO, DEBUG, etc)
        log_file_path: Path to log file. Parent directories created automatically.
    """
    numeric_level = getattr(logging, log_level.upper(), logging.INFO)

    formatter = StructuredFormatter()

    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(numeric_level)
    console_handler.setFormatter(formatter)

    # File handler (write to logs directory)
    log_path = Path(log_file_path)
    log_path.parent.mkdir(parents=True, exist_ok=True)
    
    file_handler = logging.handlers.RotatingFileHandler(
        log_file_path,
        maxBytes=10*1024*1024,  # 10MB
        backupCount=5
    )
    file_handler.setLevel(logging.DEBUG)
    file_handler.setFormatter(formatter)

    root_logger = logging.getLogger()
    root_logger.setLevel(numeric_level)

    # Avoid duplicate handlers if setup_logging() is called multiple times
    root_logger.handlers.clear()
    root_logger.addHandler(console_handler)
    root_logger.addHandler(file_handler)

    logging.getLogger("httpx").setLevel(logging.WARNING)
    logging.getLogger("chromadb").setLevel(logging.WARNING)
    logging.getLogger("sentence_transformers").setLevel(logging.WARNING)
    logging.getLogger("uvicorn.access").setLevel(logging.WARNING)


def get_logger(name: str) -> logging.Logger:
    """Get a logger instance with the given name."""
    return logging.getLogger(name)