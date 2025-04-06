import os
import structlog
import logging
from typing import Optional

def setup_logging(log_level: Optional[str] = None, log_format: Optional[str] = None) -> None:
    """
    Configure the logging system.
    
    Args:
        log_level: The logging level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
        log_format: The log format (json or console)
    """
    # Default to environment variables if not provided
    log_level = log_level or os.getenv("LOG_LEVEL", "INFO")
    log_format = log_format or os.getenv("LOG_FORMAT", "json")

    # Convert string level to logging level
    try:
        level = getattr(logging, log_level.upper())
    except AttributeError:
        raise ValueError(f"Invalid log level: {log_level}")

    # Configure standard logging
    logging.basicConfig(level=level)

    # Configure structlog
    processors = [
        structlog.stdlib.filter_by_level,
        structlog.processors.add_log_level,
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.processors.StackInfoRenderer(),
    ]

    if log_format == "json":
        processors.append(structlog.processors.JSONRenderer())
    else:
        processors.append(structlog.processors.KeyValueRenderer())

    structlog.configure(
        processors=processors,
        wrapper_class=structlog.stdlib.BoundLogger,
        context_class=dict,
        logger_factory=structlog.stdlib.LoggerFactory(),
        cache_logger_on_first_use=True,
    )

def get_logger(name: str) -> structlog.stdlib.BoundLogger:
    """
    Get a logger instance with the given name.
    
    Args:
        name: The name of the logger
        
    Returns:
        A configured logger instance
    """
    return structlog.get_logger(name) 