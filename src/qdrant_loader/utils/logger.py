import os
import structlog
import logging
from typing import Optional, Dict, Any

class QdrantVersionFilter(logging.Filter):
    """Filter to suppress Qdrant version check warnings."""
    def filter(self, record):
        return "Failed to obtain server version" not in str(record.msg)

def _error_processor(logger: Any, method_name: str, event_dict: Dict[str, Any]) -> Dict[str, Any]:
    """
    Process the error field in log messages.
    
    Args:
        logger: The logger instance
        method_name: The log method name
        event_dict: The event dictionary containing log fields
        
    Returns:
        The processed event dictionary
    """
    if "error" in event_dict:
        error = event_dict.pop("error")
        if isinstance(error, str):
            event_dict["error"] = {"message": error}
        elif isinstance(error, dict) and "message" not in error:
            event_dict["error"] = {"message": str(error)}
        
        # Ensure error is included in the event message if no event is specified
        if "event" not in event_dict:
            event_dict["event"] = str(event_dict["error"]["message"])
    
    return event_dict

def setup_logging(level: str = "INFO") -> None:
    """Configure the logging system."""
    try:
        # Convert string level to logging level
        numeric_level = getattr(logging, level.upper())
    except AttributeError:
        raise ValueError(f"Invalid log level: {level}")

    # Configure standard logging
    logging.basicConfig(
        level=numeric_level,
        format="%(message)s",
    )

    # Add filter to suppress Qdrant version check warnings
    qdrant_logger = logging.getLogger("qdrant_client")
    qdrant_logger.addFilter(QdrantVersionFilter())

    # Configure structlog
    structlog.configure(
        processors=[
            structlog.stdlib.filter_by_level,
            structlog.stdlib.add_logger_name,
            structlog.stdlib.add_log_level,
            structlog.stdlib.PositionalArgumentsFormatter(),
            structlog.processors.TimeStamper(fmt="iso"),
            _error_processor,
            structlog.processors.StackInfoRenderer(),
            structlog.processors.format_exc_info,
            structlog.processors.UnicodeDecoder(),
            structlog.stdlib.ProcessorFormatter.wrap_for_formatter,
        ],
        logger_factory=structlog.stdlib.LoggerFactory(),
        wrapper_class=structlog.stdlib.BoundLogger,
        cache_logger_on_first_use=True,
    )

    # Configure the root logger's level
    logging.getLogger().setLevel(numeric_level)

def get_logger(name: Optional[str] = None) -> structlog.BoundLogger:
    """Get a logger instance."""
    return structlog.get_logger(name) 