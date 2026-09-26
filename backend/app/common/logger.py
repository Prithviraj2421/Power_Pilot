import logging
import sys
import time
from typing import Any, Callable


def get_logger(name: str = "PowerPilot") -> logging.Logger:
    """
    Get structured logger configured with stdout stream handler and standard format.
    """
    logger = logging.getLogger(name)
    if not logger.handlers:
        logger.setLevel(logging.INFO)
        handler = logging.StreamHandler(sys.stdout)
        formatter = logging.Formatter(
            "[%(asctime)s] [%(levelname)s] [%(name)s] %(message)s",
            datefmt="%Y-%m-%d %H:%M:%S",
        )
        handler.setFormatter(formatter)
        logger.addHandler(handler)
    return logger


def log_execution_time(logger: logging.Logger, action_name: str) -> Callable[..., Any]:
    """
    Decorator to log execution timing of functions.
    """
    def decorator(func: Callable[..., Any]) -> Callable[..., Any]:
        def wrapper(*args: Any, **kwargs: Any) -> Any:
            start_time = time.perf_counter()
            logger.info(f"Starting {action_name}...")
            try:
                result = func(*args, **kwargs)
                elapsed_ms = (time.perf_counter() - start_time) * 1000
                logger.info(f"Completed {action_name} in {elapsed_ms:.2f}ms")
                return result
            except Exception as e:
                elapsed_ms = (time.perf_counter() - start_time) * 1000
                logger.error(f"Failed {action_name} after {elapsed_ms:.2f}ms - Error: {str(e)}")
                raise
        return wrapper
    return decorator
