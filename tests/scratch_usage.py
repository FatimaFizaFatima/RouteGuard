import asyncio
from app.db.db import init_db
from app.db.usage import compute_cost, save_usage
from app.config import ModelConfig

priced = ModelConfig(
    id="paid", provider="x", model="m", tasks=["chat"],
    cost_per_1m_input=0.15, cost_per_1m_output=0.60,
    max_context=4096, quality=5,
)
print(round(compute_cost(priced, 2000, 500), 6))   


async def main():
    db = await init_db("test_usage.db")
    await save_usage(db, request_id="req_1", task_type="chat", model_used="local-fast",
                     attempts=[], input_tokens=30, output_tokens=8,
                     cost=0.0, latency_ms=1200.5, status="success")
    await save_usage(db, request_id=None, task_type="code", model_used=None,
                     attempts=["local-balanced: circuit open"], input_tokens=0,
                     output_tokens=0, cost=0.0, latency_ms=5.0,
                     status="failed", error_type="AllModelsFailed")
    cur = await db.execute("SELECT * FROM requests")
    for row in await cur.fetchall():
        print(row)
    await db.close()

asyncio.run(main())