from typing import List, Set, Dict

class TransitionMemory:
    """Tracks state transitions to detect and prevent infinite loops in the reflexion graph."""

    def __init__(self):
        self.seen_sqls: Set[str] = set()
        self.seen_errors: Set[str] = set()

    def update(self, sql: str, error: str):
        self.seen_sqls.add(sql.strip())
        self.seen_errors.add(error.strip())

    def is_looping(self, sql: str, error: str) -> bool:
        """Detect if we are repeating the exact same SQL or getting the exact same error."""
        if sql.strip() in self.seen_sqls:
            return True
        # Note: sometimes the same error is expected for different SQLs, 
        # but the same (SQL, Error) pair definitely indicates a loop.
        return False
