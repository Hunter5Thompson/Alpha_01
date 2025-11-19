"""Retry logic for API calls with exponential backoff."""
from __future__ import annotations

import logging
import time
from functools import wraps
from typing import Callable, TypeVar, Any

logger = logging.getLogger(__name__)

T = TypeVar('T')


def retry_with_exponential_backoff(
    max_retries: int = 3,
    initial_delay: float = 1.0,
    exponential_base: float = 2.0,
    max_delay: float = 60.0,
    retryable_exceptions: tuple = (Exception,),
) -> Callable[[Callable[..., T]], Callable[..., T]]:
    """
    Decorator for retrying functions with exponential backoff.

    Args:
        max_retries: Maximum number of retry attempts
        initial_delay: Initial delay in seconds before first retry
        exponential_base: Multiplier for exponential backoff
        max_delay: Maximum delay between retries
        retryable_exceptions: Tuple of exception types to retry on

    Returns:
        Decorated function with retry logic
    """
    def decorator(func: Callable[..., T]) -> Callable[..., T]:
        @wraps(func)
        def wrapper(*args: Any, **kwargs: Any) -> T:
            delay = initial_delay

            for attempt in range(max_retries + 1):
                try:
                    return func(*args, **kwargs)
                except retryable_exceptions as e:
                    if attempt == max_retries:
                        logger.error(
                            "Failed after %d attempts: %s",
                            max_retries + 1,
                            str(e)
                        )
                        raise

                    # Calculate next delay with exponential backoff
                    delay = min(delay * exponential_base, max_delay)

                    logger.warning(
                        "Attempt %d/%d failed: %s. Retrying in %.2f seconds...",
                        attempt + 1,
                        max_retries + 1,
                        str(e),
                        delay
                    )

                    time.sleep(delay)

            # This should never be reached, but satisfies type checker
            raise RuntimeError("Retry logic error")

        return wrapper
    return decorator


__all__ = ["retry_with_exponential_backoff"]
