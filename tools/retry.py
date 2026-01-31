"""
Retry logic for API calls and network operations
"""
import time
from typing import Callable, TypeVar, Optional
from functools import wraps

T = TypeVar('T')


def retry(
    max_attempts: int = 3,
    delay: float = 1.0,
    backoff: float = 2.0,
    exceptions: tuple = (Exception,),
    on_retry: Optional[Callable] = None
):
    """
    Decorator to retry a function on failure.
    
    Args:
        max_attempts: Maximum number of retry attempts
        delay: Initial delay between retries (seconds)
        backoff: Multiplier for delay on each retry
        exceptions: Tuple of exceptions to catch and retry
        on_retry: Optional callback function called on each retry
    """
    def decorator(func: Callable[..., T]) -> Callable[..., T]:
        @wraps(func)
        def wrapper(*args, **kwargs) -> T:
            current_delay = delay
            last_exception = None
            
            for attempt in range(1, max_attempts + 1):
                try:
                    return func(*args, **kwargs)
                
                except exceptions as e:
                    last_exception = e
                    
                    if attempt == max_attempts:
                        # Last attempt failed, raise exception
                        raise
                    
                    # Call retry callback if provided
                    if on_retry:
                        on_retry(attempt, e, current_delay)
                    
                    # Wait before retrying
                    time.sleep(current_delay)
                    current_delay *= backoff
            
            # Should never reach here, but just in case
            if last_exception:
                raise last_exception
        
        return wrapper
    
    return decorator


def retry_api_call(max_attempts: int = 3):
    """
    Specialized retry decorator for API calls.
    Handles common API errors with appropriate delays.
    """
    from openai import APIError, RateLimitError, APIConnectionError
    
    def on_retry(attempt: int, error: Exception, delay: float):
        """Log retry attempts"""
        error_type = type(error).__name__
        print(f"⚠️  API call failed ({error_type}), retrying in {delay:.1f}s... (attempt {attempt})")
    
    return retry(
        max_attempts=max_attempts,
        delay=2.0,  # Start with 2 seconds for API calls
        backoff=2.0,
        exceptions=(APIError, RateLimitError, APIConnectionError, Exception),
        on_retry=on_retry
    )
