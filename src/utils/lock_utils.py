"""
Utility functions for file locking with automatic cleanup.
"""

import os
from functools import wraps
from pathlib import Path
from typing import Callable, TypeVar

from filelock import FileLock

T = TypeVar("T")


def with_lock_cleanup(
    lock_file_path: str | Path,
) -> Callable[[Callable[..., T]], Callable[..., T]]:
    """
    Decorator factory that ensures lock files are cleaned up after method execution.

    Args:
        lock_file_path: Path to the lock file to be cleaned up. Can be a string or Path object.

    The decorator will:
    1. Create a FileLock for the given path
    2. Acquire the lock before executing the method
    3. Execute the method
    4. Clean up the lock file after the method completes

    Example:
        LOCK_FILE = "myfile.json.lock"

        @with_lock_cleanup(LOCK_FILE)
        def my_method(self):
            # Method implementation that needs file locking
            pass
    """
    # Convert to string once at decoration time
    lock_path_str = str(lock_file_path)

    def decorator(method: Callable[..., T]) -> Callable[..., T]:
        @wraps(method)
        def wrapper(*args, **kwargs):
            lock = FileLock(lock_path_str, timeout=10)
            try:
                with lock:
                    return method(*args, **kwargs)
            finally:
                # Clean up the lock file if it exists
                if os.path.exists(lock_path_str):
                    try:
                        os.remove(lock_path_str)
                    except Exception:
                        pass  # Lock file may be in use by another process

        return wrapper

    return decorator
