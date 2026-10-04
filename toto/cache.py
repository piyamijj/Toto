"""Sunucusuz ortam için basit, süreç içi TTL önbellek."""
import time
from functools import wraps


def ttl_cache(seconds):
    def deco(fn):
        store = {}

        @wraps(fn)
        def wrapper(*args):
            now = time.monotonic()
            hit = store.get(args)
            if hit and now - hit[0] < seconds:
                return hit[1]
            value = fn(*args)
            store[args] = (now, value)
            return value

        wrapper.cache_clear = store.clear
        return wrapper

    return deco
