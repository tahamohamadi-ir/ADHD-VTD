from typing import Optional
from src.reflexion.error_taxonomy import classify_error


class RetryPolicy:
    """Encapsulates the logic for whether a retry should be attempted."""

    def __init__(self, max_retries: int = 3):
        self.max_retries = max_retries

    def should_retry(self, retry_count: int, error_msg: Optional[str] = None) -> bool:
        if retry_count >= self.max_retries:
            return False

        if error_msg:
            taxon = classify_error(error_msg)
            if not taxon.is_retryable:
                return False

        return True
