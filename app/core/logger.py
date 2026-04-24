import logging
import sys
from app.core.config import settings

# Configure logging format
LOG_FORMAT = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
LOG_LEVEL = logging.DEBUG if not settings.is_production else logging.INFO

# Create logger
logger = logging.getLogger("careops")
logger.setLevel(LOG_LEVEL)

# Console handler
console_handler = logging.StreamHandler(sys.stdout)
console_handler.setLevel(LOG_LEVEL)
console_handler.setFormatter(logging.Formatter(LOG_FORMAT))

# Add handler to logger
logger.addHandler(console_handler)


def log_info(message: str):
    """Log info level message."""
    logger.info(message)


def log_error(message: str, exc_info=None):
    """Log error level message."""
    logger.error(message, exc_info=exc_info)


def log_warning(message: str):
    """Log warning level message."""
    logger.warning(message)


def log_debug(message: str):
    """Log debug level message."""
    logger.debug(message)
