import json
from datetime import datetime, timezone, timedelta



def compute_cost(model, input_tokens: int, output_tokens: int) -> float:
    return (input_tokens / 1_000_000) * model.cost_per_1m_input \
         + (output_tokens / 1_000_000) * model.cost_per_1m_output


async def save_usage(db, *, request_id, task_type, model_used, attempts,
                     input_tokens, output_tokens, cost, latency_ms,
                     status, error_type=None):
    await db.execute(
        """INSERT INTO requests
           (ts, request_id, task_type, model_used, attempts,
            input_tokens, output_tokens, cost, latency_ms, status, error_type)
           VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
        (
            datetime.now(timezone.utc).isoformat(),
            request_id, task_type, model_used, json.dumps(attempts),
            input_tokens, output_tokens, cost, latency_ms,
            status, error_type,
        ),
    )
    await db.commit()


async def log_request(db, models, req, total_ms, resp=None, attempts=None, error_type=None):
    try:
        if resp is not None:
            model = models[resp.gateway.model_used]
            cost = compute_cost(model, resp.usage.input_tokens, resp.usage.output_tokens)
            await save_usage(
                db, request_id=resp.id, task_type=req.task_type,
                model_used=resp.gateway.model_used, attempts=resp.gateway.attempts,
                input_tokens=resp.usage.input_tokens, output_tokens=resp.usage.output_tokens,
                cost=cost, latency_ms=total_ms, status="success",
            )
        else:
            await save_usage(
                db, request_id=None, task_type=req.task_type, model_used=None,
                attempts=attempts or [], input_tokens=0, output_tokens=0,
                cost=0.0, latency_ms=total_ms, status="failed", error_type=error_type,
            )
    except Exception as e:
        print(f"usage logging failed: {e}")



async def usage_summary(db, days: int = 7) -> dict:
    since = (datetime.now(timezone.utc) - timedelta(days=days)).isoformat()

    cur = await db.execute(
        """SELECT COUNT(*),
                  SUM(status = 'failed'),
                  SUM(status = 'success' AND attempts != '[]'),
                  COALESCE(SUM(cost), 0),
                  COALESCE(SUM(input_tokens), 0),
                  COALESCE(SUM(output_tokens), 0),
                  AVG(latency_ms)
           FROM requests WHERE ts >= ?""",
        (since,),
    )
    total, failed, fallbacks, cost, tin, tout, avg_ms = await cur.fetchone()
    failed, fallbacks = failed or 0, fallbacks or 0

    cur = await db.execute(
        """SELECT model_used, COUNT(*), COALESCE(SUM(cost), 0), AVG(latency_ms)
           FROM requests WHERE ts >= ? AND status = 'success'
           GROUP BY model_used""",
        (since,),
    )
    by_model = [
        {"model": m, "requests": n, "cost": c, "avg_latency_ms": round(a, 1)}
        for m, n, c, a in await cur.fetchall()
    ]

    cur = await db.execute(
        """SELECT task_type, COUNT(*), COALESCE(SUM(cost), 0)
           FROM requests WHERE ts >= ? GROUP BY task_type""",
        (since,),
    )
    by_task = [{"task_type": t, "requests": n, "cost": c} for t, n, c in await cur.fetchall()]

    return {
        "window_days": days,
        "total_requests": total,
        "failed_requests": failed,
        "failure_rate": round(failed / total, 3) if total else 0,
        "fallback_requests": fallbacks,
        "total_cost": cost,
        "input_tokens": tin,
        "output_tokens": tout,
        "avg_latency_ms": round(avg_ms, 1) if avg_ms is not None else None,
        "by_model": by_model,
        "by_task": by_task,
    }



