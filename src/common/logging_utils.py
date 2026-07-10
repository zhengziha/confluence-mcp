import logging
import sys
from logging.handlers import RotatingFileHandler


def configure_logging(
    log_level: str = "INFO", log_file: str = "confluence-mcp-server.log"
):
    logger = logging.getLogger("confluence-mcp-server")
    logger.setLevel(getattr(logging, log_level.upper()))
    logger.propagate = False

    if logger.handlers:
        return

    formatter = logging.Formatter(
        "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    )

    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(logging.INFO)
    console_handler.setFormatter(formatter)
    logger.addHandler(console_handler)

    file_handler = RotatingFileHandler(
        log_file, maxBytes=10 * 1024 * 1024, backupCount=5
    )
    file_handler.setLevel(logging.DEBUG)
    file_handler.setFormatter(formatter)
    logger.addHandler(file_handler)