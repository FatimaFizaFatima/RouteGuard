import time
import uuid

import httpx

from app.adapters.base import ProviderAdapter
from app.errors import NonRetryableError, RetryableError
from app.schemas import ChatRequest, ChatResponse, GatewayMeta, Usage


def _retry_after(r: httpx.Response) -> float | None:
    value = r.headers.get("retry-after")
    try:
        return float(value) if value else None
    except ValueError:
        return None


class GeminiAdapter(ProviderAdapter):
    BASE_URL = "https://generativelanguage.googleapis.com/v1beta/models"

    def __init__(self, http_client, api_key: str):
        super().__init__(http_client)
        self.api_key = api_key

    async def chat(self, req: ChatRequest, model_cfg) -> ChatResponse:
       
        system_parts = [{"text": m.content} for m in req.messages if m.role == "system"]
        contents = [
            {
                "role": "model" if m.role == "assistant" else "user",
                "parts": [{"text": m.content}],
            }
            for m in req.messages
            if m.role != "system"
        ]
        if not contents:
            raise NonRetryableError("gemini needs at least one non-system message")

        generation_config = {"temperature": req.temperature}
        if req.max_tokens:
            generation_config["maxOutputTokens"] = req.max_tokens

        payload = {"contents": contents, "generationConfig": generation_config}
        if system_parts:
            payload["systemInstruction"] = {"parts": system_parts}

        t0 = time.perf_counter()
        try:
            r = await self.http.post(
                f"{self.BASE_URL}/{model_cfg.model}:generateContent",
                json=payload,
                headers={"x-goog-api-key": self.api_key},
                timeout=model_cfg.timeout_s,
            )
        except httpx.TransportError as e:
            raise RetryableError(f"gemini unreachable: {type(e).__name__}")

        if r.status_code == 429 or r.status_code >= 500:
            raise RetryableError(f"gemini status {r.status_code}: {r.text[:200]}", retry_after=_retry_after(r))
        if r.status_code >= 400:
            raise NonRetryableError(f"gemini status {r.status_code}: {r.text[:300]}")

        data = r.json()
        candidates = data.get("candidates") or []
        parts = candidates[0].get("content", {}).get("parts", []) if candidates else []
        text = "".join(p.get("text", "") for p in parts)
        if not text:
            reason = (candidates[0].get("finishReason") if candidates
                      else data.get("promptFeedback", {}).get("blockReason"))
            raise NonRetryableError(f"gemini returned no text (reason: {reason})")

        usage = data.get("usageMetadata", {})
        input_tokens = usage.get("promptTokenCount", 0)
        output_tokens = usage.get("candidatesTokenCount", 0) + usage.get("thoughtsTokenCount", 0)
        latency_ms = (time.perf_counter() - t0) * 1000
        raw_reason = candidates[0].get("finishReason")
        finish_reason = {"STOP": "stop", "MAX_TOKENS": "length"}.get(
            raw_reason, raw_reason.lower() if raw_reason else None
        )
        return ChatResponse(
            id=f"req_{uuid.uuid4().hex[:12]}",
            content=text,
            usage=Usage(input_tokens=input_tokens, output_tokens=output_tokens),
            gateway=GatewayMeta(
                model_used=model_cfg.id,
                latency_ms=round(latency_ms, 1),
                finish_reason=finish_reason,
            ),
        )