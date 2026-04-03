from abc import ABC, abstractmethod
from typing import Dict, Any

class LLMClient(ABC):
    @abstractmethod
    async def generate_response(self, prompt: str, **kwargs) -> str:
        pass

class OpenAIClient(LLMClient):
    def __init__(self, api_key: str):
        from openai import AsyncOpenAI
        self.client = AsyncOpenAI(api_key=api_key)

    async def generate_response(self, prompt: str, **kwargs) -> str:
        response = await self.client.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=[{"role": "user", "content": prompt}],
            **kwargs
        )
        return response.choices[0].message.content

class AnthropicClient(LLMClient):
    def __init__(self, api_key: str):
        import anthropic
        self.client = anthropic.AsyncAnthropic(api_key=api_key)

    async def generate_response(self, prompt: str, **kwargs) -> str:
        response = await self.client.messages.create(
            model="claude-3-sonnet-20240229",
            max_tokens=1000,
            messages=[{"role": "user", "content": prompt}],
            **kwargs
        )
        return response.content[0].text

class LLMFactory:
    @staticmethod
    def create_client(provider: str, api_key: str) -> LLMClient:
        if provider.lower() == "openai":
            return OpenAIClient(api_key)
        elif provider.lower() == "anthropic":
            return AnthropicClient(api_key)
        else:
            raise ValueError(f"Unsupported LLM provider: {provider}")