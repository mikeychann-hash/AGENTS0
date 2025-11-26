from contextlib import contextmanager

try:
    import resource  # type: ignore
except ImportError:  # pragma: no cover
    resource = None  # type: ignore

try:
    import signal
except ImportError:  # pragma: no cover
    signal = None  # type: ignore


@contextmanager
def limit_resources(cpu_seconds: int = 5, mem_mb: int = 512):
    """Context manager to limit CPU time and address space (best-effort)."""
    if resource:
        try:
            resource.setrlimit(resource.RLIMIT_CPU, (cpu_seconds, cpu_seconds))
            mem_bytes = mem_mb * 1024 * 1024
            resource.setrlimit(resource.RLIMIT_AS, (mem_bytes, mem_bytes))
        except Exception:
            pass
    yield


def install_timeout(seconds: int = 10):
    if not signal:
        return

    def _handle_timeout(signum, frame):  # noqa: ANN001, D401
        raise TimeoutError("execution timed out")

    signal.signal(signal.SIGALRM, _handle_timeout)
    signal.alarm(seconds)
