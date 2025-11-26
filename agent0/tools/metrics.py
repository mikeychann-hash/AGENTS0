import time
from contextlib import contextmanager
from typing import Dict


@contextmanager
def timed(label: str, bucket: Dict[str, float]):
    start = time.perf_counter()
    yield
    elapsed = time.perf_counter() - start
    bucket[label] = bucket.get(label, 0.0) + elapsed
