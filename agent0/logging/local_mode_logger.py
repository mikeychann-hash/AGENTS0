import logging
from logging.handlers import RotatingFileHandler
from pathlib import Path


def configure_local_development_logging(log_dir: Path, level: int = logging.INFO) -> logging.Logger:
    """
    Configure logging for local development mode with prominent warnings.

    Logs to rotating files and emits console warnings only for important events.
    """
    log_dir.mkdir(parents=True, exist_ok=True)

    logger = logging.getLogger("agent0")
    logger.setLevel(level)
    logger.handlers.clear()

    formatter = logging.Formatter(
        "[LOCAL MODE] %(asctime)s | %(levelname)s | %(name)s | %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )

    file_handler = RotatingFileHandler(log_dir / "agent0_local.log", maxBytes=10 * 1024 * 1024, backupCount=5)
    file_handler.setLevel(level)
    file_handler.setFormatter(formatter)
    logger.addHandler(file_handler)

    console_handler = logging.StreamHandler()
    console_handler.setLevel(logging.WARNING)
    console_formatter = logging.Formatter("[LOCAL] %(levelname)s: %(message)s")
    console_handler.setFormatter(console_formatter)
    logger.addHandler(console_handler)

    code_exec_handler = RotatingFileHandler(
        log_dir / "code_execution.log",
        maxBytes=5 * 1024 * 1024,
        backupCount=3,
    )
    code_exec_handler.setLevel(logging.WARNING)
    code_exec_handler.setFormatter(formatter)
    logger.addHandler(code_exec_handler)

    logger.warning("=" * 60)
    logger.warning("LOCAL DEVELOPMENT MODE ACTIVE")
    logger.warning("Code will execute directly on your machine (no isolation).")
    logger.warning("Review sandbox/ and runs/ artifacts after execution.")
    logger.warning("=" * 60)

    return logger
