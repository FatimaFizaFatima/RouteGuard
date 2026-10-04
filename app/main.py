from contextlib import asynccontextmanager

import httpx
from fastapi import FastAPI

from app.adapters.ollama import OllamaAdapter
from app.api.routes import api_router
from app.breakers import CircuitBreaker
from app.config import load_models, load_routing
from app.db.db import init_db
from app.adapters.gemini import GeminiAdapter
from app.config import Settings, load_models, load_routing


@asynccontextmanager
async def lifespan(app: FastAPI):
    settings = Settings()
    app.state.http = httpx.AsyncClient()

    adapters = {"ollama": OllamaAdapter(app.state.http)}
    if settings.gemini_api_key:
        adapters["gemini"] = GeminiAdapter(app.state.http, settings.gemini_api_key)
    app.state.adapters = adapters

    all_models = load_models("models.yaml")
    app.state.models = {mid: m for mid, m in all_models.items() if m.provider in adapters}
    skipped = sorted(set(all_models) - set(app.state.models))
    if skipped:
        print(f"skipping models with no adapter: {skipped}")
    app.state.strategies, app.state.routes = load_routing("models.yaml")
    app.state.latency = {}
    app.state.breakers = {mid: CircuitBreaker() for mid in app.state.models}
    app.state.db = await init_db("usage.db")
    yield
    await app.state.http.aclose()
    await app.state.db.close()


app = FastAPI(title="RouteGuard", lifespan=lifespan)
app.include_router(api_router)


@app.get("/health")
async def health():
    return {"status": "ok"}