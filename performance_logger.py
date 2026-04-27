"""
performance_logger.py — Lightweight profiling for Shadow.

Usage
─────
    from performance_logger import timeit

    @timeit
    def my_function():
        ...

    # Or inline:
    timeit(my_function)()

Logging is ONLY active when config.json has "debug": true.
In production (debug=false) the decorator adds zero overhead — it returns
the original function unchanged.
"""

import time
import functools
import logging

# Configure logger
logger = logging.getLogger("Shadow")
if not logger.handlers:
    handler = logging.StreamHandler()
    formatter = logging.Formatter('%(asctime)s [%(levelname)s] %(message)s', datefmt='%H:%M:%S')
    handler.setFormatter(formatter)
    logger.addHandler(handler)
    logger.setLevel(logging.INFO)


def timeit(func):
    """
    Decorator that logs execution time in ms when debug mode is active.
    Zero cost in production — skips wrapping entirely.
    """
    # Late import to avoid circular dependency (config_manager imports nothing else)
    try:
        from config_manager import config_manager
        debug = config_manager.get("debug", False)
    except Exception:
        debug = False

    if not debug:
        return func   # No wrapper — no overhead

    @functools.wraps(func)
    def wrapper(*args, **kwargs):
        t0     = time.perf_counter()
        result = func(*args, **kwargs)
        elapsed_ms = (time.perf_counter() - t0) * 1000
        print(f"[PERF] {func.__qualname__} took {elapsed_ms:.1f} ms")
        return result

    return wrapper
