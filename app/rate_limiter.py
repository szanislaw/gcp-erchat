# app/rate_limiter.py
"""
Rate limiting and request queue management for the NLQ API.
Implements token bucket algorithm and request queuing for model inference.
"""

import time
import threading
import asyncio
from collections import deque
from dataclasses import dataclass, field
from typing import Dict, Optional, Callable, Any
from functools import wraps
import logging

logger = logging.getLogger(__name__)


@dataclass
class RateLimitConfig:
    """Configuration for rate limiting"""
    requests_per_second: float = 2.0  # Max requests per second
    burst_size: int = 10  # Max burst capacity
    queue_size: int = 100  # Max queued requests
    queue_timeout: float = 30.0  # Max time to wait in queue (seconds)


@dataclass
class RateLimitResult:
    """Result of rate limit check"""
    allowed: bool
    retry_after: Optional[float] = None
    queue_position: Optional[int] = None
    message: str = ""


class TokenBucket:
    """
    Token bucket rate limiter implementation.
    Thread-safe and supports burst traffic.
    """
    
    def __init__(self, rate: float, capacity: int):
        """
        Initialize token bucket.
        
        Args:
            rate: Tokens per second to add
            capacity: Maximum token capacity
        """
        self.rate = rate
        self.capacity = capacity
        self.tokens = capacity
        self.last_update = time.time()
        self._lock = threading.Lock()
    
    def _refill(self):
        """Refill tokens based on elapsed time"""
        now = time.time()
        elapsed = now - self.last_update
        self.tokens = min(self.capacity, self.tokens + elapsed * self.rate)
        self.last_update = now
    
    def consume(self, tokens: int = 1) -> bool:
        """
        Try to consume tokens from the bucket.
        
        Args:
            tokens: Number of tokens to consume
            
        Returns:
            True if tokens were available, False otherwise
        """
        with self._lock:
            self._refill()
            if self.tokens >= tokens:
                self.tokens -= tokens
                return True
            return False
    
    def time_until_available(self, tokens: int = 1) -> float:
        """
        Calculate time until tokens will be available.
        
        Args:
            tokens: Number of tokens needed
            
        Returns:
            Seconds until tokens available (0 if already available)
        """
        with self._lock:
            self._refill()
            if self.tokens >= tokens:
                return 0.0
            needed = tokens - self.tokens
            return needed / self.rate


class RequestQueue:
    """
    Request queue for managing model inference requests.
    Ensures fair ordering and prevents queue overflow.
    """
    
    def __init__(self, max_size: int = 100, timeout: float = 30.0):
        """
        Initialize request queue.
        
        Args:
            max_size: Maximum queue size
            timeout: Default timeout for queue operations
        """
        self.max_size = max_size
        self.timeout = timeout
        self._queue: deque = deque()
        self._lock = threading.Lock()
        self._condition = threading.Condition(self._lock)
        self._processing = False
        self._current_request_id: Optional[str] = None
    
    @property
    def size(self) -> int:
        """Current queue size"""
        with self._lock:
            return len(self._queue)
    
    @property
    def is_full(self) -> bool:
        """Check if queue is full"""
        return self.size >= self.max_size
    
    def enqueue(self, request_id: str, timeout: Optional[float] = None) -> bool:
        """
        Add request to queue and wait for turn.
        
        Args:
            request_id: Unique request identifier
            timeout: Max time to wait (uses default if None)
            
        Returns:
            True if request got its turn, False if timed out
        """
        timeout = timeout or self.timeout
        deadline = time.time() + timeout
        
        with self._condition:
            # Check if queue is full
            if len(self._queue) >= self.max_size:
                logger.warning(f"Queue full, rejecting request {request_id}")
                return False
            
            # Add to queue
            self._queue.append(request_id)
            position = len(self._queue)
            logger.debug(f"Request {request_id} queued at position {position}")
            
            # Wait for turn
            while True:
                remaining = deadline - time.time()
                if remaining <= 0:
                    # Timeout - remove from queue
                    try:
                        self._queue.remove(request_id)
                    except ValueError:
                        pass
                    logger.warning(f"Request {request_id} timed out in queue")
                    return False
                
                # Check if it's our turn
                if self._queue and self._queue[0] == request_id and not self._processing:
                    self._processing = True
                    self._current_request_id = request_id
                    return True
                
                # Wait for notification
                self._condition.wait(timeout=min(remaining, 1.0))
    
    def dequeue(self, request_id: str):
        """
        Mark request as complete and allow next request.
        
        Args:
            request_id: Request identifier to dequeue
        """
        with self._condition:
            if self._queue and self._queue[0] == request_id:
                self._queue.popleft()
            self._processing = False
            self._current_request_id = None
            self._condition.notify_all()
    
    def get_position(self, request_id: str) -> int:
        """
        Get position of request in queue.
        
        Args:
            request_id: Request identifier
            
        Returns:
            Position (1-indexed) or 0 if not found
        """
        with self._lock:
            try:
                return list(self._queue).index(request_id) + 1
            except ValueError:
                return 0


class RateLimiter:
    """
    Combined rate limiter with token bucket and request queue.
    Provides both rate limiting and fair request ordering.
    """
    
    def __init__(self, config: Optional[RateLimitConfig] = None):
        """
        Initialize rate limiter.
        
        Args:
            config: Rate limit configuration
        """
        self.config = config or RateLimitConfig()
        self.bucket = TokenBucket(
            rate=self.config.requests_per_second,
            capacity=self.config.burst_size
        )
        self.queue = RequestQueue(
            max_size=self.config.queue_size,
            timeout=self.config.queue_timeout
        )
        
        # Per-client rate limiting (optional)
        self._client_buckets: Dict[str, TokenBucket] = {}
        self._client_lock = threading.Lock()
    
    def get_client_bucket(self, client_id: str) -> TokenBucket:
        """Get or create rate limiter for specific client"""
        with self._client_lock:
            if client_id not in self._client_buckets:
                self._client_buckets[client_id] = TokenBucket(
                    rate=self.config.requests_per_second,
                    capacity=self.config.burst_size
                )
            return self._client_buckets[client_id]
    
    def check_rate_limit(self, client_id: Optional[str] = None) -> RateLimitResult:
        """
        Check if request is within rate limits.
        
        Args:
            client_id: Optional client identifier for per-client limiting
            
        Returns:
            RateLimitResult with status and info
        """
        # Check global rate limit
        if not self.bucket.consume():
            retry_after = self.bucket.time_until_available()
            return RateLimitResult(
                allowed=False,
                retry_after=retry_after,
                message=f"Rate limit exceeded. Retry after {retry_after:.2f}s"
            )
        
        # Check per-client rate limit if client_id provided
        if client_id:
            client_bucket = self.get_client_bucket(client_id)
            if not client_bucket.consume():
                retry_after = client_bucket.time_until_available()
                return RateLimitResult(
                    allowed=False,
                    retry_after=retry_after,
                    message=f"Per-client rate limit exceeded. Retry after {retry_after:.2f}s"
                )
        
        return RateLimitResult(
            allowed=True,
            queue_position=self.queue.size + 1,
            message="Request allowed"
        )
    
    def acquire(self, request_id: str, timeout: Optional[float] = None) -> bool:
        """
        Acquire slot for request processing (rate limit + queue).
        
        Args:
            request_id: Unique request identifier
            timeout: Max time to wait
            
        Returns:
            True if slot acquired, False otherwise
        """
        # Check rate limit first
        result = self.check_rate_limit()
        if not result.allowed:
            logger.warning(f"Request {request_id} rate limited: {result.message}")
            return False
        
        # Queue for processing
        return self.queue.enqueue(request_id, timeout)
    
    def release(self, request_id: str):
        """
        Release slot after request processing.
        
        Args:
            request_id: Request identifier
        """
        self.queue.dequeue(request_id)
    
    def get_stats(self) -> Dict[str, Any]:
        """Get rate limiter statistics"""
        return {
            "queue_size": self.queue.size,
            "queue_max": self.config.queue_size,
            "tokens_available": self.bucket.tokens,
            "requests_per_second": self.config.requests_per_second,
            "burst_capacity": self.config.burst_size
        }


# Global rate limiter instance
_rate_limiter: Optional[RateLimiter] = None


def get_rate_limiter() -> RateLimiter:
    """Get or create global rate limiter instance"""
    global _rate_limiter
    if _rate_limiter is None:
        _rate_limiter = RateLimiter(RateLimitConfig(
            requests_per_second=2.0,
            burst_size=10,
            queue_size=50,
            queue_timeout=60.0
        ))
    return _rate_limiter


def rate_limit(func: Callable) -> Callable:
    """
    Decorator for rate limiting functions.
    
    Usage:
        @rate_limit
        def my_endpoint(request_id: str, ...):
            ...
    """
    @wraps(func)
    def wrapper(*args, **kwargs):
        request_id = kwargs.get('request_id') or f"req-{time.time()}"
        limiter = get_rate_limiter()
        
        if not limiter.acquire(request_id, timeout=30.0):
            raise Exception("Rate limit exceeded or queue timeout")
        
        try:
            return func(*args, **kwargs)
        finally:
            limiter.release(request_id)
    
    return wrapper
