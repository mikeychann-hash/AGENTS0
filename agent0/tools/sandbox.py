from contextlib import contextmanager
import logging

logger = logging.getLogger(__name__)


@contextmanager
def limit_resources(cpu_seconds: int = 5, mem_mb: int = 512):
    """
    LOCAL DEVELOPMENT MODE: No resource limits enforced.

    This is a no-op context manager for local development. Code runs directly on
    your machine with no isolation or resource limits. Only run trusted code.
    """
    logger.warning("Running in local mode - NO RESOURCE LIMITS OR ISOLATION")
    yield


def install_timeout(seconds: int = 10):
    """
    LOCAL DEVELOPMENT MODE: No timeout enforcement.

    This is a no-op function for local development.
    """
    logger.warning("Running in local mode - NO TIMEOUT ENFORCEMENT")
    pass
