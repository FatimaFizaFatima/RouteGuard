from abc import ABC, abstractmethod
from app.schemas import ChatRequest, ChatResponse


class ProviderAdapter(ABC):
    def __init__(self, http_client):
        self.http = http_client          

    @abstractmethod
    async def chat(self, req: ChatRequest, model_cfg) -> ChatResponse:
        """Send the request to the provider and return a gateway-format response."""