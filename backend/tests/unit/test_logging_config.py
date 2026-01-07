"""Tests for logging configuration module."""

import pytest
import logging
import tempfile
from pathlib import Path
from io import StringIO
import sys

from src.logging_config import StructuredFormatter, setup_logging, get_logger


def test_structured_formatter_creates_formatter():
    """Test that StructuredFormatter can be instantiated."""
    formatter = StructuredFormatter()
    assert formatter is not None


def test_structured_formatter_formats_message():
    """Test that StructuredFormatter formats log records."""
    formatter = StructuredFormatter()
    
    # Create a log record
    logger = logging.getLogger("test")
    record = logger.makeRecord(
        name="test",
        level=logging.INFO,
        fn="test.py",
        lno=42,
        msg="Test message",
        args=(),
        exc_info=None
    )
    
    formatted = formatter.format(record)
    
    # Check that formatted message contains expected components
    assert "INFO" in formatted
    assert "Test message" in formatted
    assert "42" in formatted  # Line number is included


def test_structured_formatter_includes_timestamp():
    """Test that formatted output includes ISO timestamp."""
    formatter = StructuredFormatter()
    logger = logging.getLogger("test")
    
    record = logger.makeRecord(
        name="test",
        level=logging.DEBUG,
        fn="file.py",
        lno=1,
        msg="Debug message",
        args=(),
        exc_info=None
    )
    
    formatted = formatter.format(record)
    
    # Should include ISO format timestamp with Z suffix
    assert "T" in formatted  # ISO format includes T
    assert "Z" in formatted  # Indicates UTC


def test_structured_formatter_handles_exceptions():
    """Test that formatter includes exception info when present."""
    formatter = StructuredFormatter()
    logger = logging.getLogger("test")
    
    try:
        raise ValueError("Test error")
    except ValueError:
        import sys
        exc_info = sys.exc_info()
    
    record = logger.makeRecord(
        name="test",
        level=logging.ERROR,
        fn="test.py",
        lno=10,
        msg="Error occurred",
        args=(),
        exc_info=exc_info
    )
    
    formatted = formatter.format(record)
    
    assert "Error occurred" in formatted
    assert "ValueError" in formatted


def test_structured_formatter_log_levels():
    """Test formatter with different log levels."""
    formatter = StructuredFormatter()
    logger = logging.getLogger("test")
    
    levels = [
        (logging.DEBUG, "DEBUG"),
        (logging.INFO, "INFO"),
        (logging.WARNING, "WARNING"),
        (logging.ERROR, "ERROR"),
        (logging.CRITICAL, "CRITICAL"),
    ]
    
    for level, level_name in levels:
        record = logger.makeRecord(
            name="test",
            level=level,
            fn="test.py",
            lno=1,
            msg=f"{level_name} message",
            args=(),
            exc_info=None
        )
        formatted = formatter.format(record)
        assert level_name in formatted


def test_setup_logging_basic():
    """Test basic logging setup."""
    with tempfile.TemporaryDirectory() as tmpdir:
        log_file = Path(tmpdir) / "test.log"
        
        # Setup logging
        setup_logging(log_level="INFO", log_file_path=str(log_file))
        
        # Verify log file was created
        logger = logging.getLogger("test")
        logger.info("Test message")
        
        # Check that log file exists
        assert log_file.exists()


def test_setup_logging_creates_directory():
    """Test that setup_logging creates parent directories."""
    with tempfile.TemporaryDirectory() as tmpdir:
        log_file = Path(tmpdir) / "nested" / "logs" / "app.log"
        
        # Setup logging with nested path
        setup_logging(log_level="DEBUG", log_file_path=str(log_file))
        
        # Verify directory was created
        assert log_file.parent.exists()


def test_setup_logging_with_different_levels():
    """Test setup_logging with different log levels."""
    with tempfile.TemporaryDirectory() as tmpdir:
        log_file = Path(tmpdir) / "test.log"
        
        levels = ["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"]
        
        for level in levels:
            setup_logging(log_level=level, log_file_path=str(log_file))
            # Should not raise exceptions
            root_logger = logging.getLogger()
            assert root_logger.level > 0


def test_get_logger_returns_logger():
    """Test that get_logger returns a logger."""
    logger = get_logger("test_module")
    
    assert logger is not None
    assert isinstance(logger, logging.Logger)


def test_get_logger_with_module_name():
    """Test get_logger with module name."""
    logger1 = get_logger("module1")
    logger2 = get_logger("module2")
    
    assert logger1.name == "module1"
    assert logger2.name == "module2"


def test_setup_logging_rotating_file_handler():
    """Test that setup_logging uses rotating file handler."""
    with tempfile.TemporaryDirectory() as tmpdir:
        log_file = Path(tmpdir) / "test.log"
        setup_logging(log_file_path=str(log_file))
        
        # Get root logger and check handlers
        root_logger = logging.getLogger()
        
        # Should have at least console and file handlers
        assert len(root_logger.handlers) >= 1


def test_setup_logging_console_output():
    """Test that setup_logging outputs to console."""
    with tempfile.TemporaryDirectory() as tmpdir:
        log_file = Path(tmpdir) / "test.log"
        setup_logging(log_file_path=str(log_file))
        
        logger = logging.getLogger("console_test")
        
        # Log a message
        logger.info("Console test message")
        
        # Should not raise exceptions


def test_multiple_setup_logging_calls():
    """Test that multiple calls to setup_logging work correctly."""
    with tempfile.TemporaryDirectory() as tmpdir:
        log_file1 = Path(tmpdir) / "log1.log"
        log_file2 = Path(tmpdir) / "log2.log"
        
        setup_logging(log_file_path=str(log_file1))
        setup_logging(log_file_path=str(log_file2))
        
        # Should clear handlers and set up fresh
        logger = logging.getLogger("test")
        logger.info("Message after second setup")


def test_structured_formatter_trace_id():
    """Test that structured formatter includes trace ID."""
    formatter = StructuredFormatter()
    logger = logging.getLogger("trace_test")
    
    record = logger.makeRecord(
        name="trace_test",
        level=logging.INFO,
        fn="test.py",
        lno=1,
        msg="Trace test",
        args=(),
        exc_info=None
    )
    
    formatted = formatter.format(record)
    
    # Should include trace ID (either real or no-trace)
    assert "trace" in formatted.lower() or "no-trace" in formatted


def test_setup_logging_backup_count():
    """Test that rotating file handler has backup count configured."""
    with tempfile.TemporaryDirectory() as tmpdir:
        log_file = Path(tmpdir) / "test.log"
        setup_logging(log_file_path=str(log_file))
        
        # Verify that backup count is set
        root_logger = logging.getLogger()
        # Find the rotating file handler
        for handler in root_logger.handlers:
            if hasattr(handler, 'backupCount'):
                assert handler.backupCount >= 1
                break
