"""
File locking utilities for preventing race conditions in concurrent access.
"""

import os
import threading
import time
from contextlib import contextmanager
from pathlib import Path
from typing import Optional

import logging

logger = logging.getLogger(__name__)


class FileLock:
    """Cross-platform file locking mechanism using lock files."""
    
    def __init__(self, lock_file: Path, timeout: float = 10.0, check_interval: float = 0.1):
        self.lock_file = lock_file
        self.timeout = timeout
        self.check_interval = check_interval
        self._thread_lock = threading.Lock()
        self._is_locked = False
        self._lock_file_path = lock_file.with_suffix(lock_file.suffix + '.lock')
    
    def acquire(self) -> bool:
        """Acquire the file lock with timeout."""
        with self._thread_lock:
            if self._is_locked:
                return True
            
            start_time = time.time()
            
            while True:
                try:
                    # Try to create lock file exclusively
                    try:
                        # Check if lock file exists and is not stale
                        if self._lock_file_path.exists():
                            lock_stat = self._lock_file_path.stat()
                            if time.time() - lock_stat.st_mtime > self.timeout:
                                # Stale lock, remove it
                                self._lock_file_path.unlink(missing_ok=True)
                                logger.warning(f"Removed stale lock file: {self._lock_file_path}")
                            else:
                                # Lock is held by another process
                                if time.time() - start_time > self.timeout:
                                    logger.error(f"Failed to acquire lock within timeout: {self._lock_file_path}")
                                    return False
                                
                                time.sleep(self.check_interval)
                                continue
                        
                        # Create lock file
                        self._lock_file_path.touch(exist_ok=False)
                        self._is_locked = True
                        logger.debug(f"Acquired file lock: {self._lock_file_path}")
                        return True
                        
                    except FileExistsError:
                        # Lock file was created by another process
                        if time.time() - start_time > self.timeout:
                            logger.error(f"Failed to acquire lock within timeout: {self._lock_file_path}")
                            return False
                        
                        time.sleep(self.check_interval)
                        
                except Exception as e:
                    logger.error(f"Error acquiring lock {self._lock_file_path}: {e}")
                    return False
    
    def release(self) -> bool:
        """Release the file lock."""
        with self._thread_lock:
            if not self._is_locked:
                return True
            
            try:
                if self._lock_file_path.exists():
                    self._lock_file_path.unlink()
                self._is_locked = False
                logger.debug(f"Released file lock: {self._lock_file_path}")
                return True
            except OSError as e:
                logger.error(f"Error releasing lock {self._lock_file_path}: {e}")
                return False
    
    def __enter__(self):
        self.acquire()
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        self.release()


@contextmanager
def file_lock(file_path: Path, timeout: float = 10.0, check_interval: float = 0.1):
    """Context manager for file locking."""
    lock = FileLock(file_path, timeout, check_interval)
    try:
        if lock.acquire():
            yield lock
        else:
            raise TimeoutError(f"Could not acquire lock for {file_path}")
    finally:
        lock.release()


def with_file_lock(func):
    """Decorator that adds file locking to functions that operate on files."""
    def wrapper(*args, **kwargs):
        # Extract file path from arguments (common patterns)
        file_path = None
        for arg in args:
            if isinstance(arg, (str, Path)):
                file_path = Path(arg)
                break
        
        if file_path is None:
            # Try kwargs
            for key, value in kwargs.items():
                if isinstance(value, (str, Path)) and any(term in key.lower() for term in ['file', 'path', 'output']):
                    file_path = Path(value)
                    break
        
        if file_path:
            with file_lock(file_path):
                return func(*args, **kwargs)
        else:
            # No file path found, call function without lock
            return func(*args, **kwargs)
    
    return wrapper