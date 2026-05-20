_C=True
_B=False
_A=None
import time,threading,asyncio
from collections import deque
from dataclasses import dataclass,field
from typing import Dict,Optional,Callable,Any
from functools import wraps
import logging
logger=logging.getLogger(__name__)
@dataclass
class RateLimitConfig:requests_per_second:float=2.;burst_size:int=10;queue_size:int=100;queue_timeout:float=3e1
@dataclass
class RateLimitResult:allowed:bool;retry_after:Optional[float]=_A;queue_position:Optional[int]=_A;message:str=''
class TokenBucket:
	def __init__(self,rate,capacity):self.rate=rate;self.capacity=capacity;self.tokens=capacity;self.last_update=time.time();self._lock=threading.Lock()
	def _refill(self):now=time.time();elapsed=now-self.last_update;self.tokens=min(self.capacity,self.tokens+elapsed*self.rate);self.last_update=now
	def consume(self,tokens=1):
		with self._lock:
			self._refill()
			if self.tokens>=tokens:self.tokens-=tokens;return _C
			return _B
	def time_until_available(self,tokens=1):
		with self._lock:
			self._refill()
			if self.tokens>=tokens:return .0
			needed=tokens-self.tokens;return needed/self.rate
class RequestQueue:
	def __init__(self,max_size=100,timeout=3e1):self.max_size=max_size;self.timeout=timeout;self._queue=deque();self._lock=threading.Lock();self._condition=threading.Condition(self._lock);self._processing=_B;self._current_request_id=_A
	@property
	def size(self):
		with self._lock:return len(self._queue)
	@property
	def is_full(self):return self.size>=self.max_size
	def enqueue(self,request_id,timeout=_A):
		timeout=timeout or self.timeout;deadline=time.time()+timeout
		with self._condition:
			if len(self._queue)>=self.max_size:logger.warning(f"Queue full, rejecting request {request_id}");return _B
			self._queue.append(request_id);position=len(self._queue);logger.debug(f"Request {request_id} queued at position {position}")
			while _C:
				remaining=deadline-time.time()
				if remaining<=0:
					try:self._queue.remove(request_id)
					except ValueError:pass
					logger.warning(f"Request {request_id} timed out in queue");return _B
				if self._queue and self._queue[0]==request_id and not self._processing:self._processing=_C;self._current_request_id=request_id;return _C
				self._condition.wait(timeout=min(remaining,1.))
	def dequeue(self,request_id):
		with self._condition:
			if self._queue and self._queue[0]==request_id:self._queue.popleft()
			self._processing=_B;self._current_request_id=_A;self._condition.notify_all()
	def get_position(self,request_id):
		with self._lock:
			try:return list(self._queue).index(request_id)+1
			except ValueError:return 0
class RateLimiter:
	def __init__(self,config=_A):self.config=config or RateLimitConfig();self.bucket=TokenBucket(rate=self.config.requests_per_second,capacity=self.config.burst_size);self.queue=RequestQueue(max_size=self.config.queue_size,timeout=self.config.queue_timeout);self._client_buckets={};self._client_lock=threading.Lock()
	def get_client_bucket(self,client_id):
		with self._client_lock:
			if client_id not in self._client_buckets:self._client_buckets[client_id]=TokenBucket(rate=self.config.requests_per_second,capacity=self.config.burst_size)
			return self._client_buckets[client_id]
	def check_rate_limit(self,client_id=_A):
		if not self.bucket.consume():retry_after=self.bucket.time_until_available();return RateLimitResult(allowed=_B,retry_after=retry_after,message=f"Rate limit exceeded. Retry after {retry_after:.2f}s")
		if client_id:
			client_bucket=self.get_client_bucket(client_id)
			if not client_bucket.consume():retry_after=client_bucket.time_until_available();return RateLimitResult(allowed=_B,retry_after=retry_after,message=f"Per-client rate limit exceeded. Retry after {retry_after:.2f}s")
		return RateLimitResult(allowed=_C,queue_position=self.queue.size+1,message='Request allowed')
	def acquire(self,request_id,timeout=_A):
		result=self.check_rate_limit()
		if not result.allowed:logger.warning(f"Request {request_id} rate limited: {result.message}");return _B
		return self.queue.enqueue(request_id,timeout)
	def release(self,request_id):self.queue.dequeue(request_id)
	def get_stats(self):return{'queue_size':self.queue.size,'queue_max':self.config.queue_size,'tokens_available':self.bucket.tokens,'requests_per_second':self.config.requests_per_second,'burst_capacity':self.config.burst_size}
_rate_limiter=_A
def get_rate_limiter():
	global _rate_limiter
	if _rate_limiter is _A:_rate_limiter=RateLimiter(RateLimitConfig(requests_per_second=2.,burst_size=10,queue_size=50,queue_timeout=6e1))
	return _rate_limiter
def rate_limit(func):
	@wraps(func)
	def wrapper(*args,**kwargs):
		request_id=kwargs.get('request_id')or f"req-{time.time()}";limiter=get_rate_limiter()
		if not limiter.acquire(request_id,timeout=3e1):raise Exception('Rate limit exceeded or queue timeout')
		try:return func(*args,**kwargs)
		finally:limiter.release(request_id)
	return wrapper