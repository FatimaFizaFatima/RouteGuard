from app.errors import NonRetryableError, RetryableError
from app.schemas import ChatRequest, ChatResponse
import asyncio
import random

MAX_RETRIES = 1        
BASE_DELAY = 0.5       
MAX_DELAY = 5.0  
EWMA_ALPHA = 0.3


class AllModelsFailed(Exception):
    def __init__(self, attempts: list[str]):
        super().__init__("all candidate models failed")
        self.attempts = attempts

async def call_with_retry(adapter, req, model):
    for attempt in range(MAX_RETRIES + 1):
        try:
            return await adapter.chat(req, model)
        except RetryableError as e:
            if attempt == MAX_RETRIES:
                raise
            if e.retry_after is not None and e.retry_after > MAX_DELAY:
                raise
            delay = e.retry_after if e.retry_after is not None else BASE_DELAY * (2 ** attempt)
            delay += random.uniform(0, delay * 0.25)
            await asyncio.sleep(delay)

async def execute(req, candidates, adapters, latency, breakers) -> ChatResponse:
    attempts: list[str] = []

    for model in candidates:
        breaker = breakers[model.id]
        if not breaker.allow():
            attempts.append(f"{model.id}: circuit open")
            continue

        adapter = adapters[model.provider]
        try:
            resp = await call_with_retry(adapter, req, model)
        except RetryableError as e:
            breaker.record_failure()
            attempts.append(f"{model.id}: {e}")
            continue
        except NonRetryableError:
            breaker.release()
            raise

        breaker.record_success()
        update_latency(latency, model.id, resp.gateway.latency_ms)
        resp.gateway.model_used = model.id
        resp.gateway.attempts = attempts
        resp.gateway.fallback_used = len(attempts) > 0
        return resp

    raise AllModelsFailed(attempts)

def update_latency(latency: dict[str, float], model_id: str, sample_ms: float) -> None:
    old = latency.get(model_id)
    if old is None:
        latency[model_id] = sample_ms          
    else:
        latency[model_id] = EWMA_ALPHA * sample_ms + (1 - EWMA_ALPHA) * old