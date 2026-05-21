"""AI 响应缓存服务"""
import time
from typing import Optional, Dict, Any
from functools import lru_cache
import hashlib
import json


class AICache:
    """简单内存缓存"""

    def __init__(self, ttl_seconds: int = 300):
        self._cache: Dict[str, tuple] = {}  # key -> (data, timestamp)
        self._ttl = ttl_seconds

    def get(self, key: str) -> Optional[Any]:
        entry = self._cache.get(key)
        if entry and time.time() - entry[1] < self._ttl:
            return entry[0]
        if key in self._cache:
            del self._cache[key]
        return None

    def set(self, key: str, value: Any):
        self._cache[key] = (value, time.time())

    def make_key(self, prompt: str, model: str = "") -> str:
        content = f"{model}:{prompt}"
        return hashlib.md5(content.encode()).hexdigest()


@lru_cache()
def get_ai_cache() -> AICache:
    return AICache()
