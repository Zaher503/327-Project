"""
transactions.py  (M4 – Transaction Management & Concurrency Control)

Provides local transaction support:
- Per-file pessimistic locking using RLocks
- Prevents concurrent writes to the same file
- Wrap DB changes in a safe context manager
"""

import threading
from contextlib import contextmanager
from typing import Dict


# Global lock table: file_id -> threading.RLock
_file_locks: Dict[str, threading.RLock] = {}
_table_lock = threading.Lock()


def _get_lock(key: str) -> threading.RLock:
    """
    Returns an existing lock for a file OR creates a new one.
    Protected by a table-level lock.
    """
    with _table_lock:
        if key not in _file_locks:
            _file_locks[key] = threading.RLock()
        return _file_locks[key]


@contextmanager
def acquire_file_lock(file_id: str):
    """
    Context manager for per-file pessimistic locking.

    Usage:
        with acquire_file_lock(file_id):
            # perform disk + db writes safely
    """
    lock = _get_lock(file_id)
    lock.acquire()
    try:
        yield
    finally:
        lock.release()
