"""请求速率限制"""
import time
import threading
from functools import lru_cache


class TokenBucket:
    """令牌桶算法限流"""

    def __init__(self, tokens_per_minute: int = 1_200_000, burst_size: int = 200_000):
        self.tokens_per_minute = tokens_per_minute
        self.burst_size = burst_size
        self.tokens = burst_size
        self.last_refill = time.monotonic()
        self.lock = threading.Lock()

    def acquire(self, tokens: int = 1) -> bool:
        """尝试获取令牌，返回是否成功"""
        with self.lock:
            now = time.monotonic()
            elapsed = now - self.last_refill
            refill = elapsed * (self.tokens_per_minute / 60.0)
            self.tokens = min(self.burst_size, self.tokens + refill)
            self.last_refill = now
            if self.tokens >= tokens:
                self.tokens -= tokens
                return True
            return False

    def wait_and_acquire(self, tokens: int = 1, timeout: float = 30.0) -> bool:
        """等待并获取令牌"""
        deadline = time.monotonic() + timeout
        while time.monotonic() < deadline:
            if self.acquire(tokens):
                return True
            time.sleep(0.1)
        return False


@lru_cache()
def get_rate_limiter() -> TokenBucket:
    return TokenBucket()
