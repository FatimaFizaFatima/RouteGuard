import asyncio
import httpx

from app.adapters.gemini import GeminiAdapter
from app.config import ModelConfig, Settings
from app.errors import NonRetryableError
from app.schemas import ChatRequest

cfg = ModelConfig(
    id="cloud-gemini", provider="gemini", model="gemini-3.8-flash",
    tasks=["chat"], cost_per_1m_input=0, cost_per_1m_output=0,
    max_context=100000, quality=9,
)
req = ChatRequest(messages=[
    {"role": "system", "content": "Answer briefly."},
    {"role": "user", "content": "What is the capital of France?"},
])


async def main():
    async with httpx.AsyncClient() as http:
        good = GeminiAdapter(http, Settings().gemini_api_key)
        print(await good.chat(req, cfg))

        bad = GeminiAdapter(http, "wrong-key")
        try:
            await bad.chat(req, cfg)
        except NonRetryableError as e:
            print("wrong key ->", type(e).__name__)

asyncio.run(main())