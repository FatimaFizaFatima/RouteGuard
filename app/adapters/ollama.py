import time
import uuid
import httpx

from app.adapters.base import ProviderAdapter
from app.errors import RetryableError, NonRetryableError
from app.schemas import ChatRequest, ChatResponse, GatewayMeta, Usage


class OllamaAdapter(ProviderAdapter):
    BASE_URL = "http://localhost:11434"

    async def chat(self, req: ChatRequest, model_cfg) -> ChatResponse:
      
        payload = {
            "model": model_cfg.model,
            "messages": [m.model_dump() for m in req.messages],
            "stream": False,
            "options": {"temperature": req.temperature},
        }
        if req.max_tokens:
            payload["options"]["num_predict"] = req.max_tokens

        t0 = time.perf_counter()
        try:
            r = await self.http.post(
                f"{self.BASE_URL}/api/chat",
                json=payload,
                timeout=model_cfg.timeout_s,
            )
        except (httpx.TimeoutException, httpx.ConnectError) as e:
            raise RetryableError(f"ollama unreachable: {type(e).__name__}")

        if r.status_code == 429 or r.status_code >= 500:
            raise RetryableError(f"ollama status {r.status_code}")
        if r.status_code >= 400:
            raise NonRetryableError(f"ollama status {r.status_code}: {r.text}")

        data = r.json()
        latency_ms = (time.perf_counter() - t0) * 1000
        return ChatResponse(
            id=f"req_{uuid.uuid4().hex[:12]}",
            content=data["message"]["content"],
            usage=Usage(
                input_tokens=data.get("prompt_eval_count", 0),
                output_tokens=data.get("eval_count", 0),
            ),
            gateway=GatewayMeta(
                model_used=model_cfg.model,
                latency_ms=round(latency_ms, 1),
            ),
        )