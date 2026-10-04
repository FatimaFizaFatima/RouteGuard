import time

from fastapi import APIRouter, BackgroundTasks, Query, Request
from fastapi.responses import JSONResponse

from app.db.usage import log_request, usage_summary
from app.errors import NonRetryableError
from app.executor import AllModelsFailed, execute
from app.router import route
from app.schemas import ChatRequest, ChatResponse

api_router = APIRouter(prefix="/v1", tags=["gateway"])


@api_router.post("/chat/completions", response_model=ChatResponse)
async def chat(req: ChatRequest, request: Request, background: BackgroundTasks):
    state = request.app.state
    t0 = time.perf_counter()

    def failure(status_code, detail, error_type, attempts=None):
        total_ms = (time.perf_counter() - t0) * 1000
        background.add_task(log_request, state.db, state.models,
                            req, total_ms, None, attempts, error_type)
        return JSONResponse(status_code=status_code, content={"detail": detail},
                            background=background)

    candidates = route(req, state.models, state.strategies,
                       state.routes, state.latency)
    if not candidates:
        return failure(422, f"no model supports task_type '{req.task_type}' for this request",
                       "NoCandidates")
    try:
        resp = await execute(req, candidates, state.adapters,
                             state.latency, state.breakers)
    except AllModelsFailed as e:
        return failure(503, {"message": "all candidate models failed", "attempts": e.attempts},
                       "AllModelsFailed", e.attempts)
    except NonRetryableError as e:
        return failure(400, str(e), "NonRetryableError")

    total_ms = (time.perf_counter() - t0) * 1000
    background.add_task(log_request, state.db, state.models, req, total_ms, resp)
    return resp


@api_router.get("/models")
async def list_models(request: Request):
    return [
        {
            "id": m.id,
            "provider": m.provider,
            "tasks": m.tasks,
            "quality": m.quality,
        }
        for m in request.app.state.models.values()
    ]


@api_router.get("/breakers")
async def breakers(request: Request):
    return {mid: b.state for mid, b in request.app.state.breakers.items()}


@api_router.get("/latency")
async def latency(request: Request):
    return request.app.state.latency


@api_router.get("/usage")
async def usage(request: Request, days: int = Query(7, ge=1, le=365)):
    return await usage_summary(request.app.state.db, days)