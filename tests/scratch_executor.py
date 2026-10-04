import asyncio
import time

from app.adapters.base import ProviderAdapter
from app.breakers import CircuitBreaker
from app.config import ModelConfig
from app.errors import NonRetryableError, RetryableError
from app.executor import AllModelsFailed, execute
from app.schemas import ChatRequest, ChatResponse, GatewayMeta, Usage


class FakeAdapter(ProviderAdapter):
    def __init__(self, behavior, fail_times=0, retry_after=None):
        self.behavior = behavior
        self.fail_times = fail_times
        self.retry_after = retry_after
        self.calls = 0

    async def chat(self, req, model_cfg):
        self.calls += 1
        if self.behavior == "outage":
            raise RetryableError("fake outage")
        if self.behavior == "flaky" and self.calls <= self.fail_times:
            raise RetryableError("fake blip")
        if self.behavior == "limited":
            raise RetryableError("fake rate limit", retry_after=self.retry_after)
        if self.behavior == "bad":
            raise NonRetryableError("fake bad request")
        return ChatResponse(
            id="req_fake",
            content="ok",
            usage=Usage(input_tokens=1, output_tokens=1),
            gateway=GatewayMeta(model_used="x", latency_ms=1.0),
        )


def fake_model(id, provider):
    return ModelConfig(
        id=id, provider=provider, model="m", tasks=["chat"],
        cost_per_1m_input=0, cost_per_1m_output=0,
        max_context=4096, quality=5,
    )


adapters = {
    "down": FakeAdapter("outage"),
    "up": FakeAdapter("ok"),
    "broken": FakeAdapter("bad"),
}
req = ChatRequest(messages=[{"role": "user", "content": "hi"}])


async def run(label, candidates):
    print(f"--- {label}")
    try:
        r = await execute(req, candidates, adapters)
        print("OK:", r.gateway.model_used, r.gateway.fallback_used, r.gateway.attempts)
    except AllModelsFailed as e:
        print("ALL FAILED:", e.attempts)
    except NonRetryableError as e:
        print("STOPPED:", e)


import app.executor as ex
ex.BASE_DELAY = 0.01    

async def breaker_cases():
    A, B = fake_model("A", "a"), fake_model("B", "b")
    latency = {}

    print("=== A is down: breaker opens, then skips A")
    adapters = {"a": FakeAdapter("outage"), "b": FakeAdapter("ok")}
    breakers = {"A": CircuitBreaker(failure_limit=1, cooldown_s=0.2),
                "B": CircuitBreaker()}
    for n in (1, 2):
        r = await execute(req, [A, B], adapters, latency, breakers)
        print(n, r.gateway.attempts, "A calls:", adapters["a"].calls, breakers["A"].state)

    print("=== cooldown ends: one probe goes to A, fails, reopens")
    time.sleep(0.25)
    r = await execute(req, [A, B], adapters, latency, breakers)
    print(3, r.gateway.attempts, "A calls:", adapters["a"].calls, breakers["A"].state)

    print("=== A recovers: probe succeeds, breaker closes")
    adapters["a"].behavior = "ok"
    time.sleep(0.25)
    r = await execute(req, [A, B], adapters, latency, breakers)
    print(4, r.gateway.model_used, r.gateway.attempts, breakers["A"].state)

    print("=== bad request must NOT trip the breaker")
    adapters = {"a": FakeAdapter("bad"), "b": FakeAdapter("ok")}
    breakers = {"A": CircuitBreaker(failure_limit=1), "B": CircuitBreaker()}
    try:
        await execute(req, [A, B], adapters, latency, breakers)
    except NonRetryableError as e:
        print("STOPPED:", e, "| A state:", breakers["A"].state, "| failures:", breakers["A"].failures)

async def case(label, adapters, candidates):
    print(f"--- {label}")
    latency = {}
    breakers = {m.id: CircuitBreaker() for m in candidates}
    try:
        r = await execute(req, candidates, adapters, latency, breakers)
        print("OK:", r.gateway.model_used, r.gateway.fallback_used, r.gateway.attempts)
    except AllModelsFailed as e:
        print("ALL FAILED:", e.attempts)
    except NonRetryableError as e:
        print("STOPPED:", e)
    print("calls:", {k: a.calls for k, a in adapters.items()}, "latency:", latency)

async def main():
    A, B = fake_model("A", "a"), fake_model("B", "b")

    await case("blip, retry saves it",
               {"a": FakeAdapter("flaky", fail_times=1), "b": FakeAdapter("ok")}, [A, B])
    await case("blip lasts too long",
               {"a": FakeAdapter("flaky", fail_times=2), "b": FakeAdapter("ok")}, [A, B])
    await case("hard outage",
               {"a": FakeAdapter("outage"), "b": FakeAdapter("ok")}, [A, B])
    await case("long retry-after skips the retry",
               {"a": FakeAdapter("limited", retry_after=30), "b": FakeAdapter("ok")}, [A, B])
    await case("short retry-after waits then falls back",
               {"a": FakeAdapter("limited", retry_after=0.05), "b": FakeAdapter("ok")}, [A, B])
    await case("bad request is never retried",
               {"a": FakeAdapter("bad"), "b": FakeAdapter("ok")}, [A, B])
    await breaker_cases()


asyncio.run(main())
